from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from agents.agents.cordinator import invoke_coordinator
from agents.agents.safety import check_prompt_safety, redact_pii
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

        if not check_prompt_safety(query):
            return Response(
                {"message": "Prompt is not safe for further processing or LLM!"},
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        query = redact_pii(query)

        try:
            # Call the coordinator agent
            response = None
            e = None
            for _ in range(3):
                try:
                    response = invoke_coordinator(user_input=query, user_email=user.email)
                    break
                except Exception as _e:
                    print(f"Error {_e} at retry {_}")
                    e = _e
            else:
                if e:
                    raise Exception(e)
            
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to process query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
