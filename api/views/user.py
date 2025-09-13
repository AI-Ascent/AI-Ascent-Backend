from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db.models.user import APIUser
from agents.agents.feedback import classify_feedback, summarise_feedback_points
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.core.cache import cache
import json


class AddFeedbackView(APIView):
    def post(self, request):
        email = request.data.get("email")
        feedback = request.data.get("feedback")
        if not email or not feedback:
            return Response(
                {"error": "email and feedback are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = APIUser.objects.get(email=email)

            # Invalidate old cache before adding new feedback
            old_feedbacks_tuple = tuple(user.feedbacks)
            classify_key = f"classify_feedback_{hash(old_feedbacks_tuple)}"
            
            # Since generate_insights depends on classify_feedback, we need to get the old classified result to build its key
            old_classified_result = cache.get(classify_key)
            if old_classified_result:
                insights_key = f"generate_insights_{hash(json.dumps(old_classified_result, sort_keys=True))}"
                cache.delete(insights_key)

            cache.delete(classify_key)
            
            # Invalidate opportunity agent cache for all possible top_k values
            for i in range(1, 6): # Clear for top_k=1 to 5
                opportunity_key = f"find_mentors_{email}_{i}"
                cache.delete(opportunity_key)

            user.feedbacks.append(feedback)
            user.save()
            return Response(
                {"message": "Feedback added successfully"}, status=status.HTTP_200_OK
            )
        except APIUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class ClassifyFeedbackView(APIView):
    @method_decorator(cache_page(60 * 60 * 24 * 2))  # Cache for 2 days
    @method_decorator(vary_on_cookie)
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = APIUser.objects.get(email=email)
            if not user.feedbacks:
                return Response(
                    {"error": "No feedbacks found for this user"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            classified = classify_feedback(user.feedbacks)
            return Response(
                {"classified_feedback": classified}, status=status.HTTP_200_OK
            )
        except APIUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class SummariseFeedbackView(APIView):
    @method_decorator(cache_page(60 * 60 * 24 * 2))  # Cache for 2 days
    @method_decorator(vary_on_cookie)
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = APIUser.objects.get(email=email)
            if not user.feedbacks:
                return Response(
                    {"error": "No feedbacks found for this user"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            summary = summarise_feedback_points(user.feedbacks)
            user.strengths = summary["strengths_insights"]
            user.improvements = summary["improvements_insights"]
            user.save()
            return Response(
                {"summary": summary}, status=status.HTTP_200_OK
            )
        except APIUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


