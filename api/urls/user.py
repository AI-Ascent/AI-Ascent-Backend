from django.urls import path
from api.views.user import AddFeedbackView, ClassifyFeedbackView

urlpatterns = [
    path('add-feedback/', AddFeedbackView.as_view(), name='add-feedback'),
    path('classify-feedback/', ClassifyFeedbackView.as_view(), name='classify-feedback'),
]
