from django.conf import settings
from rest_framework.request import Request
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"

    def allow_request(self, request: Request, view: APIView) -> bool:
        if getattr(settings, "AUTH_THROTTLE_DISABLED", False):
            return True
        return super().allow_request(request, view)
