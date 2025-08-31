from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db.models.user import APIUser


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
