from django.urls import path
from api.views.auth import AuthenticateUser

urlpatterns = [
    path('login/', AuthenticateUser.as_view(), name='authenticate'),
]
