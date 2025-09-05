from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db.models.user import APIUser

class AuthenticateUser(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = APIUser.objects.get(email=email)
            if user.check_password(password):
                return Response({"message": "Authentication successful."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid password."}, status=status.HTTP_401_UNAUTHORIZED)
        except APIUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        