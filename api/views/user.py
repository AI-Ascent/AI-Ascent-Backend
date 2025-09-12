from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db.models.user import APIUser
from agents.agents.feedback import classify_feedback, summarise_feedback_points


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


