from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db.models.onboard import OnboardCatalog

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
        
        if not isinstance(tags, list) or not isinstance(checklist, list) or not isinstance(resources, list):
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
                {"message": "Onboarding item created successfully", "id": onboard_item.id},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to create onboarding item: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
