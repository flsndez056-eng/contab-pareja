import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("contab.private_monitoring")


class PrivateMonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "server_error request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )
            raise
        response.headers["X-Request-ID"] = request_id
        if response.status_code >= 500:
            logger.error(
                "server_response_error request_id=%s status=%s method=%s path=%s",
                request_id,
                response.status_code,
                request.method,
                request.url.path,
            )
        return response
