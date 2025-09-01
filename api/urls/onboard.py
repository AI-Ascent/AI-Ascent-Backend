from django.urls import path
from api.views.onboard import CreateOnboardView

urlpatterns = [
    path('onboard/create/', CreateOnboardView.as_view(), name='create_onboard'),
]