from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from agents.agents.cordinator import invoke_coordinator
from db.models.user import APIUser
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class CoordinatorView(APIView):
    permission_classes = [IsAuthenticated]
    
    @method_decorator(cache_page(60 * 60 * 24 * 2))  # Cache for 2 days
    def post(self, request):
        # Get user from JWT token
        user = request.user
        query = request.data.get("query")

        if not query:
            return Response(
                {"error": "Query is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Call the coordinator agent
            response = invoke_coordinator(user_input=query, user_email=user.email)
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to process query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
