from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from db.models.kpi import KPI
from db.models.user import APIUser
from db.models.feedback import NegativeFeedback
from agents.agents.feedback import classify_feedback, summarise_feedback_points
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.core.cache import cache
import json
import threading


def process_feedback_background(user_email: str, new_feedbacks: list = []):
    """
    Background function to process feedback summarization.
    This runs in a separate thread to avoid blocking the API response.
    """
    try:
        user = APIUser.objects.get(email=user_email)
        classify_feedback(user.feedbacks, True)
        summary = summarise_feedback_points(new_feedbacks)
        user.strengths.extend(summary["strengths_insights"])
        user.improvements.extend(summary["improvements_insights"])
        user.save()
        
        # Save each new improvement insight as a NegativeFeedback entry
        for improvement in summary["improvements_insights"]:
            NegativeFeedback.objects.create(user=user, feedback_text=improvement)
        
        print(f"Successfully processed feedback for {user_email}")
    except Exception as e:
        print(f"Background task failed to process feedback for {user_email}: {str(e)}")


class AddFeedbackView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Get the authenticated user from JWT token
        authenticated_user = request.user
        
        email = request.data.get("email")
        feedback = request.data.get("feedback")
        
        if not email or not feedback:
            return Response(
                {"error": "email and feedback are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check that user is not adding feedback for themselves
        if authenticated_user.email == email:
            return Response(
                {"error": "You cannot add feedback for yourself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = APIUser.objects.get(email=email)

            new_feedbacks = [fi for fi in feedback.split(".") if fi.strip()]
            user.feedbacks.extend(new_feedbacks)
            user.save()
            
            kpi = KPI.create_or_get_current_month()
            kpi.total_feedbacks_count += len(new_feedbacks)
            kpi.save()

            # Start background processing of feedback summarization
            thread = threading.Thread(
                target=process_feedback_background, 
                args=(email,new_feedbacks),
                daemon=True
            )
            thread.start()
            
            return Response(
                {"message": "Feedback added successfully"}, status=status.HTTP_200_OK
            )
        except APIUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class ClassifyFeedbackView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Get user from JWT token
        user = request.user
        
        if not user.feedbacks:
            return Response(
                {"error": "No feedbacks found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )
        classified = classify_feedback(user.feedbacks)
        return Response(
            {"classified_feedback": classified}, status=status.HTTP_200_OK
        )


class SummariseFeedbackView(APIView):
    permission_classes = [IsAuthenticated]
    
    @method_decorator(cache_page(60 * 60 * 24 * 2))  # Cache for 2 days
    @method_decorator(vary_on_cookie)
    def post(self, request):
        # Get user from JWT token
        user = request.user
        
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


