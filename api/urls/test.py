from django.urls import path
from api.views.test import AddFeedbackView

urlpatterns = [
    path('add-feedback/', AddFeedbackView.as_view(), name='add-feedback'),
]
