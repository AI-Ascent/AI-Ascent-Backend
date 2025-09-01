from django.urls import path
from api.views.onboard import CreateOnboardView, GetOnboardView

urlpatterns = [
    path('onboard/create/', CreateOnboardView.as_view(), name='create_onboard'),
    path('onboard/get/', GetOnboardView.as_view(), name='get_onboard'),
]