from django.urls import path
from api.views.skill import CreateSkillView, GetSkillRecommendationsView

urlpatterns = [
    path('create-skill/', CreateSkillView.as_view(), name='create-skill'),
    path('get-skill-recommendations/', GetSkillRecommendationsView.as_view(), name='get-skill-recommendations'),
]
