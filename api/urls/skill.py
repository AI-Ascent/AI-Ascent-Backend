from django.urls import path
from api.views.skill import CreateSkillView, GetSkillRecommendationsView, UpdateSkillView, ListSkillView, DeleteSkillView

urlpatterns = [
    path('create-skill/', CreateSkillView.as_view(), name='create-skill'),
    path('get-skill-recommendations/', GetSkillRecommendationsView.as_view(), name='get-skill-recommendations'),
    path('update-skill/', UpdateSkillView.as_view(), name='update-skill'),
    path('list-skill/', ListSkillView.as_view(), name='list-skill'),
    path('delete-skill/', DeleteSkillView.as_view(), name='delete-skill'),
]
