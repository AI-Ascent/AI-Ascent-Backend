from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from db.models.user import APIUser
from agents.agents.feedback import classify_feedback, summarise_feedback_points
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.core.cache import cache
import json
import threading


def process_feedback_background(user_email: str):
    """
    Background function to process feedback summarization.
    This runs in a separate thread to avoid blocking the API response.
    """
    try:
        user = APIUser.objects.get(email=user_email)
        summary = summarise_feedback_points(user.feedbacks)
        user.strengths = summary["strengths_insights"]
        user.improvements = summary["improvements_insights"]
        user.save()
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

            user.feedbacks.extend(feedback.split("."))
            user.save()
            
            # Start background processing of feedback summarization
            thread = threading.Thread(
                target=process_feedback_background, 
                args=(email,),
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


