from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from db.models.onboard import OnboardCatalog
from agents.agents.onboard import run_onboard_agent
from db.models.user import APIUser
from agents.agents.safety import check_prompt_safety, redact_pii
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class CreateOnboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        title = request.data.get("title")
        specialization = request.data.get("specialization")
        tags = request.data.get("tags")
        checklist = request.data.get("checklist")
        resources = request.data.get("resources")

        if not title:
            return Response(
                {"error": "title and specialization are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            not isinstance(tags, list)
            or not isinstance(checklist, list)
            or not isinstance(resources, list)
        ):
            return Response(
                {"error": "tags, checklist, and resources must be arrays"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            onboard_item = OnboardCatalog.objects.create(
                title=title,
                specialization=specialization,
                tags=tags,
                checklist=checklist,
                resources=resources,
            )
            return Response(
                {
                    "message": "Onboarding item created successfully",
                    "id": onboard_item.id,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to create onboarding item: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetOnboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    @method_decorator(cache_page(60 * 60 * 24 * 2))  # Cache for 2 days
    def post(self, request):
        # Get user from JWT token
        employee = request.user
        additional_prompt = request.data.get("additional_prompt", "")

        if not check_prompt_safety(additional_prompt):
            return Response(
                {"message": "Prompt is not safe for further processing or LLM!"},
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        
        additional_prompt = redact_pii(additional_prompt)

        job_title = employee.job_title
        specialization = employee.specialization

        try:
            result = None
            e = None
            for _ in range(3):
                try:
                    result = run_onboard_agent(additional_prompt, job_title, specialization)
                    break
                except Exception as _e:
                    print(f"Error {_e} at retry {_}")
                    e = _e
            else:
                if e:
                    raise Exception(e)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to run onboard agent: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
