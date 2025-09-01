from .user import urlpatterns as test_patterns
from .onboard import urlpatterns as onboard_patterns

urlpatterns = test_patterns + onboard_patterns
