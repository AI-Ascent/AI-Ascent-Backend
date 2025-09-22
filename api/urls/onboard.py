from django.urls import path
from api.views.onboard import CreateOnboardView, GetOnboardView, UpdateOnboardView, ListOnboardView, DeleteOnboardView

urlpatterns = [
    path('onboard/create/', CreateOnboardView.as_view(), name='create_onboard'),
    path('onboard/get/', GetOnboardView.as_view(), name='get_onboard'),
    path('onboard/update/', UpdateOnboardView.as_view(), name='update_onboard'),
    path('onboard/list/', ListOnboardView.as_view(), name='list_onboard'),
    path('onboard/delete/', DeleteOnboardView.as_view(), name='delete_onboard'),
]