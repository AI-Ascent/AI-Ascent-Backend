from django.urls import path
from api.views.cordinator import CoordinatorView

urlpatterns = [
    path('coordinator-ask/', CoordinatorView.as_view(), name='coordinator-ask'),
]