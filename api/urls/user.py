from django.urls import path
from api.views.user import AddFeedbackView, ClassifyFeedbackView, SummariseFeedbackView

urlpatterns = [
    path('add-feedback/', AddFeedbackView.as_view(), name='add-feedback'),
    path('classify-feedback/', ClassifyFeedbackView.as_view(), name='classify-feedback'),
    path('summarise-feedback/', SummariseFeedbackView.as_view(), name='summarise-feedback'),
]
