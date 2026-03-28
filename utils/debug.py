import pocketbase
import os
import time
from dotenv import load_dotenv

from utils.logger import log_db, error_logger
from utils import metrics as m

load_dotenv()


class Debug:
    def __init__(self, client: pocketbase.PocketBase | None):
        self.client = client

    def send_error(self, error_message, school, page, status):
        if self.client is None:
            return
        if os.environ.get("ENV") != "production":
            return

        start = time.perf_counter()
        try:
            r = self.client.collection("debug").create(
                {
                    "error_message": error_message,
                    "school": school,
                    "page": page,
                    "status": status,
                }
            )
            duration_ms = (time.perf_counter() - start) * 1000
            m.PB_OPERATIONS_TOTAL.labels(
                collection="debug", operation="create", status="success"
            ).inc()
            m.PB_OPERATION_DURATION_SECONDS.labels(
                collection="debug", operation="create"
            ).observe(duration_ms / 1000)
            log_db(
                collection="debug",
                operation="create",
                status="success",
                duration_ms=duration_ms,
                record_id=r.id,
            )
            return r.id
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            m.PB_OPERATIONS_TOTAL.labels(
                collection="debug", operation="create", status="error"
            ).inc()
            log_db(
                collection="debug",
                operation="create",
                status="error",
                duration_ms=duration_ms,
                error=str(exc),
            )
            return
