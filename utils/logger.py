import logging
import json
import os
import traceback
from datetime import datetime, timezone
from typing import Any

import logging_loki


_ENV = os.environ.get("APP_ENV", "development")
_LOG_LEVEL = logging.DEBUG if _ENV != "production" else logging.INFO
_LOKI_URL = os.environ.get("LOKI_URL", "")
_LOKI_TOKEN = os.environ.get("LOKI_TOKEN", "")
_INSTANCE = os.environ.get("INSTANCE_ID", "default")


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "env": _ENV,
        }
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            ):
                base[key] = value
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False, default=str)


def _build_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    if _LOKI_URL:
        auth = (_LOKI_TOKEN, "") if _LOKI_TOKEN else None
        handler = logging_loki.LokiHandler(
            url=f"{_LOKI_URL.rstrip('/')}/loki/api/v1/push",
            tags={"app": "vocpass", "env": _ENV, "logger": name, "instance": _INSTANCE},
            auth=auth,
            version="1",
        )
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())

    logger.addHandler(handler)
    logger.setLevel(_LOG_LEVEL)
    logger.propagate = False
    return logger


app_logger = _build_logger("vocpass.app")
request_logger = _build_logger("vocpass.request")
school_logger = _build_logger("vocpass.school")
parse_logger = _build_logger("vocpass.parse")
db_logger = _build_logger("vocpass.db")
error_logger = _build_logger("vocpass.error")



def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    school_name: str | None = None,
    client_ip: str | None = None,
    query_params: dict | None = None,
):
    request_logger.info(
        "http request",
        extra={
            "tags": {
                "event": "http_request",
                "method": method,
                "status_code": str(status_code),
                "school_name": school_name or "unknown",
            },
            "event": "http_request",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 3),
            "school_name": school_name or "unknown",
            "client_ip": client_ip,
            "query_params": query_params or {},
        },
    )


def log_school_fetch(
    school_name: str,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
    response_size: int = 0,
    error: str | None = None,
):
    level = logging.WARNING if status_code >= 400 else logging.INFO
    school_logger.log(
        level,
        "school fetch",
        extra={
            "tags": {
                "event": "school_fetch",
                "school_name": school_name,
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code),
            },
            "event": "school_fetch",
            "school_name": school_name,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 3),
            "response_size_bytes": response_size,
            "error": error,
        },
    )


def log_parse(
    school_name: str,
    data_type: str,
    status: str,
    duration_ms: float,
    record_count: int = 0,
    error: str | None = None,
):
    level = logging.WARNING if status == "error" else logging.INFO
    parse_logger.log(
        level,
        "parse result",
        extra={
            "tags": {
                "event": "parse",
                "school_name": school_name,
                "data_type": data_type,
                "status": status,
            },
            "event": "parse",
            "school_name": school_name,
            "data_type": data_type,
            "status": status,
            "duration_ms": round(duration_ms, 3),
            "record_count": record_count,
            "error": error,
        },
    )


def log_error(
    message: str,
    school_name: str = "system",
    path: str = "",
    error_type: str = "Exception",
    error_id: str | None = None,
    exc: Exception | None = None,
):
    error_logger.error(
        message,
        extra={
            "tags": {
                "event": "error",
                "school_name": school_name,
                "error_type": error_type,
            },
            "event": "error",
            "school_name": school_name,
            "path": path,
            "error_type": error_type,
            "error_id": error_id,
            "traceback": (
                "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                if exc else None
            ),
        },
    )


def log_db(
    collection: str,
    operation: str,
    status: str,
    duration_ms: float,
    record_id: str | None = None,
    error: str | None = None,
):
    level = logging.WARNING if status == "error" else logging.DEBUG
    db_logger.log(
        level,
        "pocketbase operation",
        extra={
            "tags": {
                "event": "db_operation",
                "collection": collection,
                "operation": operation,
                "status": status,
            },
            "event": "db_operation",
            "collection": collection,
            "operation": operation,
            "status": status,
            "duration_ms": round(duration_ms, 3),
            "record_id": record_id,
            "error": error,
        },
    )


def log_startup(schools_count: int, env: str):
    app_logger.info(
        "application started",
        extra={
            "tags": {"event": "startup"},
            "event": "startup",
            "schools_count": schools_count,
            "env": env,
        },
    )
