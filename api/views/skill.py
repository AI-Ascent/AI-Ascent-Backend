from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsSuperUser
from db.models.skill import SkillCatalog, InterestedSkill
from agents.agents.skill import run_skill_agent
from db.models.user import APIUser
from agents.agents.safety import check_prompt_safety, redact_pii
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from db.models.embeddings import embeddings
from pgvector.django import CosineDistance
from django.db import transaction
from django.utils import timezone


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


class AddInterestedSkillView(APIView):
    """Accept a single skill item from frontend matching agent shape and add to user's InterestedSkill with per-user dedupe.

    Expected body:
      - title: str (required)
      - description: str (required)
      - learning_outcomes: list[str] (optional)
      - resources: list[ { title, url, type } ] (optional)

    Server sets set_at = now. Dedupe via per-user vector similarity on title only.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        title = request.data.get("skill_title")
        description = request.data.get("skill_description", "")
        learning_outcomes = request.data.get("learning_outcomes", [])
        resources = request.data.get("resources", [])

        if not title or not isinstance(title, str):
            return Response({"error": "title is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(description, str):
            return Response({"error": "description must be a string"}, status=status.HTTP_400_BAD_REQUEST)
        if learning_outcomes is not None and not isinstance(learning_outcomes, list):
            return Response({"error": "learning_outcomes must be an array of strings"}, status=status.HTTP_400_BAD_REQUEST)
        if resources is not None and not isinstance(resources, list):
            return Response({"error": "resources must be an array"}, status=status.HTTP_400_BAD_REQUEST)

        title_vec = embeddings.embed_query(title)

        # Vector similarity dedupe for this user
        top = (
            InterestedSkill.objects.filter(user=user, title_vector__isnull=False)
            .annotate(distance=CosineDistance("title_vector", title_vec))
            .order_by("distance")
            .first()
        )

        SIM_THRESHOLD = 0.90
        if top is not None:
            similarity = 1 - float(getattr(top, "distance", 1.0))
            if similarity >= SIM_THRESHOLD:
                # Update set_at and return existing
                with transaction.atomic():
                    top.set_at = timezone.now()
                    top.save(update_fields=["set_at"])
                return Response({
                    "interested_skill_id": top.id,
                    "message": "deduped by similarity",
                    "similarity": round(similarity, 4),
                }, status=status.HTTP_200_OK)

        obj = InterestedSkill.objects.create(
            user=user,
            skill_title=title,
            skill_description=description,
            learning_outcomes=learning_outcomes or [],
            resources=resources or [],
            title_vector=title_vec
        )

        return Response({
            "message": "Added skill",
            "interested_skill_id": obj.id,
        }, status=status.HTTP_201_CREATED)


class GetInterestedSkillsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        interested_skills = InterestedSkill.objects.filter(user=user).order_by('-set_at')
        data = [
            {
                "id": skill.id,
                "skill_title": skill.skill_title,
                "skill_description": skill.skill_description,
                "learning_outcomes": skill.learning_outcomes,
                "resources": skill.resources,
                "set_at": skill.set_at,
            }
            for skill in interested_skills
        ]
        return Response({"skills": data}, status=status.HTTP_200_OK)


class DeleteInterestedSkillView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        skill_id = request.data.get("id")

        if not skill_id:
            return Response({"error": "id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            skill = InterestedSkill.objects.get(id=skill_id, user=user)
        except InterestedSkill.DoesNotExist:
            return Response({"error": "Interested skill not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            skill.delete()
            return Response({"message": "Interested skill deleted successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to delete interested skill: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


