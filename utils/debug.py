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

    def send_error(self, error_message, school, page, status, response_body=None, traceback=None):
        if self.client is None:
            return
        if os.environ.get("APP_ENV") != "production":
            return

        payload = {
            "error_message": str(error_message) if error_message is not None else "",
            "school": school,
            "page": page,
            "status": status,
        }
        if response_body is not None:
            payload["response_body"] = str(response_body)[:10000]
        if traceback is not None:
            payload["traceback"] = str(traceback)[:5000]

        start = time.perf_counter()
        try:
            r = self.client.collection("debug").create(payload)
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
