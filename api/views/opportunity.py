from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from agents.agents.opportunity import find_mentors_for_improvements
from db.models.user import APIUser


class FindMentorsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Get user from JWT token
        user = request.user
        top_k = request.data.get("top_k", 3)

        if not isinstance(top_k, int) or top_k <= 0:
            return Response({"error": "top_k must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mentors = find_mentors_for_improvements(user_email=user.email, top_k=top_k)
            return Response({"mentors": mentors}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to find mentors: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
