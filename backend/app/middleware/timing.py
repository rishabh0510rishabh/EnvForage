
# --- Request Timing & Telemetry Middleware ---
import logging
import time
import uuid
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("Telemetry")

class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    A comprehensive APM (Application Performance Monitoring) middleware.
    Calculates sub-millisecond request durations, injects correlation IDs (X-Request-ID),
    and pushes structured telemetry payloads to a background queue for Prometheus/Datadog ingestion.
    """

    def __init__(self, app):
        super().__init__(app)
        # Mock telemetry queue (In real life, use Kafka, Redis Stream, or Datadog agent)
        self.telemetry_queue: list[dict[str, Any]] = []
        self.max_queue_size = 1000

    def _flush_telemetry(self):
        """Simulates pushing telemetry data to an external sink."""
        if len(self.telemetry_queue) >= self.max_queue_size:
            logger.info(f"Flushing {len(self.telemetry_queue)} telemetry events to sink...")
            # e.g., await datadog_client.push(self.telemetry_queue)
            self.telemetry_queue.clear()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()

        # Extract or generate a Correlation ID for distributed tracing
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Attach request_id to request state so routes can log it
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            logger.error(f"Request {request_id} failed with unhandled exception: {e}")
            raise e
        finally:
            process_time = time.perf_counter() - start_time
            process_time_ms = round(process_time * 1000, 2)

            # Construct telemetry event
            event = {
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "duration_ms": process_time_ms,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "timestamp": time.time()
            }

            self.telemetry_queue.append(event)
            self._flush_telemetry()

            # If the response was successful, inject headers
            # Note: We can only mutate headers if the response hasn't already started streaming
            if 'response' in locals() and hasattr(response, 'headers'):
                response.headers["X-Process-Time"] = str(process_time_ms)
                response.headers["X-Request-ID"] = request_id

        return response
