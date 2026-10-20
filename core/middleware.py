import logging
import time

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
