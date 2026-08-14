import time
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

old_factory = logging.getLogRecordFactory()

def request_id_record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    if not hasattr(record, "request_id"):
        record.request_id = "-"
    return record

logging.setLogRecordFactory(request_id_record_factory)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [request_id=%(request_id)s] %(name)s: %(message)s"
)

logger = logging.getLogger("efap")

class ContextLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(
                f"request_id={request_id} method={request.method} path={request.url.path} "
                f"status={response.status_code} duration_ms={duration_ms}"
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"request_id={request_id} method={request.method} path={request.url.path} "
                f"status=500 duration_ms={duration_ms} error={str(exc)}"
            )
            raise

