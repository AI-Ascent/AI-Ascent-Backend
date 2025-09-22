from django.urls import path
from api.views.onboard import CreateOnboardView, GetOnboardView, UpdateOnboardView, ListOnboardView, DeleteOnboardView, FinalizeOnboardView, CompleteChecklistItemView, CheckFinalizeOnboardView, GetFinalizedOnboardView

urlpatterns = [
    path('onboard/create/', CreateOnboardView.as_view(), name='create_onboard'),
    path('onboard/get/', GetOnboardView.as_view(), name='get_onboard'),
    path('onboard/update/', UpdateOnboardView.as_view(), name='update_onboard'),
    path('onboard/list/', ListOnboardView.as_view(), name='list_onboard'),
    path('onboard/delete/', DeleteOnboardView.as_view(), name='delete_onboard'),
    path('onboard/finalize/', FinalizeOnboardView.as_view(), name='finalize_onboard'),
    path('onboard/mark-checklist-item/', CompleteChecklistItemView.as_view(), name='complete_checklist_item'),
    path('onboard/check/', CheckFinalizeOnboardView.as_view(), name='check_if_finalized'),
    path('onboard/finalized/', GetFinalizedOnboardView.as_view(), name='get_finalized_onboard'),
]