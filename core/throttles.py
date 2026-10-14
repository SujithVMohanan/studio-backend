from django.conf import settings
from rest_framework.throttling import AnonRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"

    def allow_request(self, request, view):
        if getattr(settings, "AUTH_THROTTLE_DISABLED", False):
            return True
        return super().allow_request(request, view)
