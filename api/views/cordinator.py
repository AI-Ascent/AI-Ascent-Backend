from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from agents.agents.cordinator import invoke_coordinator
from db.models.user import APIUser


class CoordinatorView(APIView):
    def post(self, request):
        email = request.data.get("email")
        query = request.data.get("query")

        if not email or not query:
            return Response(
                {"error": "Email and query are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Verify user exists
            APIUser.objects.get(email=email)
        except APIUser.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Call the coordinator agent
            response = invoke_coordinator(user_input=query, user_email=email)
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to process query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
