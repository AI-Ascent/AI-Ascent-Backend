import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsSuperUser
from db.models.onboard import OnboardCatalog
from agents.agents.onboard import run_onboard_agent
from db.models.user import APIUser
from agents.agents.safety import check_prompt_safety, redact_pii


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

        hr_supp_additional_prompt = f"{additional_prompt} | Supplementary (kinda important) HR dept query: {employee.onboard_supp_hr_query}"

        job_title = employee.job_title
        specialization = employee.specialization

        try:
            result = None
            e = None
            for _ in range(3):
                try:
                    result = run_onboard_agent(
                        hr_supp_additional_prompt, job_title, specialization
                    )
                    employee.onboard_json = result
                    employee.save()
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


class UpdateOnboardView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        id = request.data.get("id")
        title = request.data.get("title")
        specialization = request.data.get("specialization")
        tags = request.data.get("tags")
        checklist = request.data.get("checklist")
        resources = request.data.get("resources")

        if not id:
            return Response(
                {"error": "id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            onboard_item = OnboardCatalog.objects.get(id=id)
        except OnboardCatalog.DoesNotExist:
            return Response(
                {"error": "Onboarding item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if tags is not None and not isinstance(tags, list):
            return Response(
                {"error": "tags must be an array"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if checklist is not None and not isinstance(checklist, list):
            return Response(
                {"error": "checklist must be an array"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if resources is not None and not isinstance(resources, list):
            return Response(
                {"error": "resources must be an array"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if title is not None:
                onboard_item.title = title
            if specialization is not None:
                onboard_item.specialization = specialization
            if tags is not None:
                onboard_item.tags = tags
            if checklist is not None:
                onboard_item.checklist = checklist
            if resources is not None:
                onboard_item.resources = resources
            onboard_item.save()
            return Response(
                {
                    "message": "Onboarding item updated successfully",
                    "id": onboard_item.id,
                    "data": {
                        "id": onboard_item.id,
                        "title": onboard_item.title,
                        "specialization": onboard_item.specialization,
                        "tags": onboard_item.tags,
                        "checklist": onboard_item.checklist,
                        "resources": onboard_item.resources,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to update onboarding item: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ListOnboardView(APIView):
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
            onboard_items = OnboardCatalog.objects.all().order_by("id")[
                index_start:index_end
            ]
            data = [
                {
                    "id": item.id,
                    "title": item.title,
                    "specialization": item.specialization,
                }
                for item in onboard_items
            ]
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to list onboarding items: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteOnboardView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        id = request.data.get("id")

        if not id:
            return Response(
                {"error": "id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            onboard_item = OnboardCatalog.objects.get(id=id)
        except OnboardCatalog.DoesNotExist:
            return Response(
                {"error": "Onboarding item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            onboard_item.delete()
            return Response(
                {"message": "Onboarding item deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete onboarding item: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FinalizeOnboardView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        employee = request.user
        employee.onboard_finalized = True
        employee.save()
        return Response(
            {"message": "Onboard finalized successfully"},
            status=status.HTTP_200_OK,
        )


class CompleteChecklistItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        checklist_item = request.data.get("checklist_item")

        if not checklist_item:
            return Response(
                {"error": "checklist_item is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee = request.user

        if checklist_item not in employee.onboard_completed_checklist_items:
            if checklist_item not in employee.onboard_json["checklist"]:
                return Response(
                    {"error": "Checklist item not in original onboard checklist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            employee.onboard_completed_checklist_items.append(checklist_item)
            employee.save()

        return Response(
            {"message": "Checklist item marked as completed"},
            status=status.HTTP_200_OK,
        )


class CheckFinalizeOnboardView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        employee = request.user
        return Response(
            {"finalized": employee.onboard_finalized},
            status=status.HTTP_200_OK,
        )


class GetFinalizedOnboardView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        employee = request.user
        return Response(
            {
                "onboard_data": employee.onboard_json,
                "completed_items": employee.onboard_completed_checklist_items,
            },
            status=status.HTTP_200_OK,
        )
