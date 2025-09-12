from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db.models.onboard import OnboardCatalog
from agents.agents.onboard import run_onboard_agent
from db.models.user import APIUser
from agents.agents.safety import check_prompt_safety


class CreateOnboardView(APIView):
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
    def post(self, request):
        email = request.data.get("email")
        additional_prompt = request.data.get("additional_prompt", "")

        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            employee = APIUser.objects.get(email=email)
        except APIUser.DoesNotExist:
            return Response(
                {"error": "Employee not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not check_prompt_safety(additional_prompt):
            return Response(
                {"message": "Prompt is not safe for further processing or LLM!"},
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        job_title = employee.job_title
        specialization = employee.specialization

        try:
            result = run_onboard_agent(additional_prompt, job_title, specialization)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to run onboard agent: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
