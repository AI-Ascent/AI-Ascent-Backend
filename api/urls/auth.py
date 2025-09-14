from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from api.views.auth import AuthenticateUser, CustomTokenObtainPairView

urlpatterns = [
    path('login/', AuthenticateUser.as_view(), name='authenticate'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
