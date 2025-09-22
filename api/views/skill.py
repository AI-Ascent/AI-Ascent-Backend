from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsSuperUser
from db.models.skill import SkillCatalog
from agents.agents.skill import run_skill_agent
from db.models.user import APIUser
from agents.agents.safety import check_prompt_safety, redact_pii
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class CreateSkillView(APIView):
    permission_classes = [IsAuthenticated]
    
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
    permission_classes = [IsAuthenticated]
    
    @method_decorator(cache_page(60 * 60 * 24 * 2))  # Cache for 2 days
    def post(self, request):
        # Get user from JWT token
        employee = request.user
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

        user_context = f"User context - Job Title: {employee.job_title}"
        if employee.specialization:
            user_context += f", Specialization: {employee.specialization}"
        user_context += ". "

        # Construct the full query
        full_query = f"{user_context}{skill_query}"

        full_query = redact_pii(full_query)

        try:
            result = None
            e = None
            for _ in range(3):
                try:
                    result = run_skill_agent(full_query.strip(), employee.email)
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
                {"error": f"Failed to get skill recommendations: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpdateSkillView(APIView):
    permission_classes = [IsSuperUser]
    
    def post(self, request):
        id = request.data.get("id")
        title = request.data.get("title")
        tags = request.data.get("tags")
        skill_type = request.data.get("type")
        url = request.data.get("url")

        if not id:
            return Response(
                {"error": "id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            skill_item = SkillCatalog.objects.get(id=id)
        except SkillCatalog.DoesNotExist:
            return Response(
                {"error": "Skill item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if tags is not None and not isinstance(tags, list):
            return Response(
                {"error": "tags must be an array"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if title is not None:
                skill_item.title = title
            if tags is not None:
                skill_item.tags = tags
            if skill_type is not None:
                skill_item.type = skill_type
            if url is not None:
                skill_item.url = url
            skill_item.save()
            return Response(
                {
                    "message": "Skill item updated successfully",
                    "id": skill_item.id,
                    "data": {
                        "id": skill_item.id,
                        "title": skill_item.title,
                        "tags": skill_item.tags,
                        "type": skill_item.type,
                        "url": skill_item.url,
                    }
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to update skill item: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ListSkillView(APIView):
    permission_classes = [IsSuperUser]
    
    def post(self, request):
        index_start = request.data.get("index_start")
        index_end = request.data.get("index_end")
        
        if index_start is None or index_end is None:
            return Response(
                {"error": "index_start and index_end must be present"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            index_start = int(index_start)
            index_end = int(index_end)
        except ValueError:
            return Response(
                {"error": "index_start and index_end must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if index_start < 0 or index_end < index_start:
            return Response(
                {"error": "Invalid index range"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            skill_items = SkillCatalog.objects.all().order_by('id')[index_start:index_end]
            data = [
                {
                    "id": item.id,
                    "title": item.title,
                    "type": item.type,
                }
                for item in skill_items
            ]
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to list skill items: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteSkillView(APIView):
    permission_classes = [IsSuperUser]
    
    def post(self, request):
        id = request.data.get("id")

        if not id:
            return Response(
                {"error": "id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            skill_item = SkillCatalog.objects.get(id=id)
        except SkillCatalog.DoesNotExist:
            return Response(
                {"error": "Skill item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            skill_item.delete()
            return Response(
                {"message": "Skill item deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete skill item: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
