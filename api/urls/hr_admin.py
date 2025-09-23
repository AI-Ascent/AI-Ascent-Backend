from django.urls import path
from api.views.hr_admin import GlobalSkillTrendsView, GlobalNegativeFeedbackTrendsView, GetKPI

urlpatterns = [
	path('global-skill-trends/', GlobalSkillTrendsView.as_view(), name='global-skill-trends'),
	path('global-negative-feedback-trends/', GlobalNegativeFeedbackTrendsView.as_view(), name='global-negative-feedback-trends'),
	path('kpi/', GetKPI.as_view(), name='kpi-last-three-months'),
]