from .user import urlpatterns as test_patterns
from .onboard import urlpatterns as onboard_patterns
from .skill import urlpatterns as skill_patterns

urlpatterns = test_patterns + onboard_patterns + skill_patterns
