import logging
import time
import uuid

from django.conf import settings
from django.shortcuts import render

logger = logging.getLogger(__name__)


class RequestTimingMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start
        logger.info(
            "%s %s -> %s in %.2fs",
            request.method,
            request.path,
            response.status_code,
            duration,
        )
        return response


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.MAINTENANCE_MODE:
            return self.get_response(request)
        if request.path.startswith(("/admin/", "/healthz/")):
            return self.get_response(request)
        if request.user.is_staff:
            return self.get_response(request)
        return render(request, "maintenance.html", status=503)
