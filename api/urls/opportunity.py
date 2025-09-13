from django.urls import path
from api.views.opportunity import FindMentorsView

urlpatterns = [
    path('find-mentors/', FindMentorsView.as_view(), name='find-mentors'),
]