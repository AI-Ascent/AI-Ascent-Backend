from rest_framework.permissions import IsAuthenticated


class IsSuperUser(IsAuthenticated):
    """
    Custom permission to only allow authenticated superusers to access the view.
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.is_superuser