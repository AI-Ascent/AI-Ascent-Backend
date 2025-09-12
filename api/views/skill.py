from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db.models.skill import SkillCatalog
from agents.agents.skill import run_skill_agent
from db.models.user import APIUser
from agents.agents.safety import check_prompt_safety, redact_pii


class CreateSkillView(APIView):
    def post(self, request):
        title = request.data.get("title")
        tags = request.data.get("tags", [])
        skill_type = request.data.get("type")
        url = request.data.get("url")

        if not title or not skill_type or not url:
            return Response(
                {"error": "title, type, and url are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(tags, list):
            return Response(
                {"error": "tags must be an array"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            skill_item = SkillCatalog.objects.create(
                title=title,
                tags=tags,
                type=skill_type,
                url=url,
            )
            return Response(
                {"message": "Skill item created successfully", "id": skill_item.id},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to create skill item: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetSkillRecommendationsView(APIView):
    def post(self, request):
        email = request.data.get("email")
        skill_query = request.data.get("skill_query")

        if not skill_query:
            return Response(
                {"error": "skill_query is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not check_prompt_safety(skill_query):
            return Response(
                {"message": "Prompt is not safe for further processing or LLM!"},
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        employee = APIUser.objects.get(email=email)
        user_context = f"User context - Job Title: {employee.job_title}"
        if employee.specialization:
            user_context += f", Specialization: {employee.specialization}"
        user_context += ". "

        # Construct the full query
        full_query = f"{user_context}{skill_query}"

        full_query = redact_pii(full_query)

        try:
            result = run_skill_agent(full_query.strip(), email)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to get skill recommendations: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
