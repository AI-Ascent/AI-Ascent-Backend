from .user import urlpatterns as test_patterns
from .onboard import urlpatterns as onboard_patterns
from .skill import urlpatterns as skill_patterns
from .auth import urlpatterns as auth_patterns
from .opportunity import urlpatterns as opportunity_patterns
from .cordinator import urlpatterns as coordinator_patterns
from .hr_admin import urlpatterns as hr_admin_patterns

urlpatterns = test_patterns + onboard_patterns + skill_patterns + auth_patterns + opportunity_patterns + coordinator_patterns + hr_admin_patterns
