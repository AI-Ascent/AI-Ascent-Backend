from django.urls import path
from api.views.hr_admin import GlobalSkillTrendsView

urlpatterns = [
	path('global-skill-trends/', GlobalSkillTrendsView.as_view(), name='global-skill-trends'),
]