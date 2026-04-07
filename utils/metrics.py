from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY
import time

HTTP_REQUESTS_TOTAL = Counter(
    "vocpass_http_requests_total",
    "API 總請求數",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "vocpass_http_request_duration_seconds",
    "API 請求處理時間（秒）",
    ["method", "path"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

HTTP_REQUEST_SIZE_BYTES = Histogram(
    "vocpass_http_request_size_bytes",
    "API 請求 body 大小（bytes）",
    ["method", "path"],
    buckets=[64, 256, 1024, 4096, 16384, 65536],
)

HTTP_RESPONSE_SIZE_BYTES = Histogram(
    "vocpass_http_response_size_bytes",
    "API 回應 body 大小（bytes）",
    ["method", "path"],
    buckets=[256, 1024, 4096, 16384, 65536, 262144],
)

HTTP_REQUESTS_IN_FLIGHT = Gauge(
    "vocpass_http_requests_in_flight",
    "目前進行中的 API 請求數",
    ["method", "path"],
)

SCHOOL_FETCH_TOTAL = Counter(
    "vocpass_school_fetch_total",
    "對學校系統的外部 HTTP 請求總數",
    ["school_name", "endpoint", "method", "status_code"],
)

SCHOOL_FETCH_DURATION_SECONDS = Histogram(
    "vocpass_school_fetch_duration_seconds",
    "爬取學校資料所需時間（秒）",
    ["school_name", "endpoint", "method"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

SCHOOL_FETCH_SIZE_BYTES = Histogram(
    "vocpass_school_fetch_response_size_bytes",
    "學校系統回應大小（bytes）",
    ["school_name", "endpoint"],
    buckets=[1024, 4096, 16384, 65536, 262144, 1048576],
)

SCHOOL_FETCH_ERRORS_TOTAL = Counter(
    "vocpass_school_fetch_errors_total",
    "爬取學校資料失敗次數",
    ["school_name", "endpoint", "error_type"],
)

PARSE_OPERATIONS_TOTAL = Counter(
    "vocpass_parse_operations_total",
    "HTML/JSON 解析操作次數",
    ["school_name", "data_type", "status"],  # data_type: merit_demerit/curriculum/attendance/...
)

PARSE_DURATION_SECONDS = Histogram(
    "vocpass_parse_duration_seconds",
    "解析操作所需時間（秒）",
    ["school_name", "data_type"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

PARSE_RECORDS_COUNT = Histogram(
    "vocpass_parse_records_count",
    "單次解析回傳的記錄筆數",
    ["school_name", "data_type"],
    buckets=[0, 1, 5, 10, 25, 50, 100, 200, 500],
)

SCHOOL_REQUESTS_TOTAL = Counter(
    "vocpass_school_requests_total",
    "各學校被查詢次數",
    ["school_name", "api_version", "data_type"],
)

SCHOOL_LOGIN_CHECKS_TOTAL = Counter(
    "vocpass_school_login_checks_total",
    "/ping 登入狀態檢查次數",
    ["school_name", "result"],  # result: logged_in / not_logged_in / error
)

SCHOOL_NOTICE_REQUESTS_TOTAL = Counter(
    "vocpass_school_notice_requests_total",
    "公告查詢次數",
    ["school_name", "api_version"],
)

ERRORS_TOTAL = Counter(
    "vocpass_errors_total",
    "應用程式錯誤總次數",
    ["school_name", "error_type", "path"],
)

HTTP_ERRORS_TOTAL = Counter(
    "vocpass_http_errors_total",
    "HTTP 錯誤回應次數（4xx/5xx）",
    ["status_code", "path"],
)

RATE_LIMIT_HITS_TOTAL = Counter(
    "vocpass_rate_limit_hits_total",
    "Rate limit 被觸發次數",
    ["path"],
)

PB_OPERATIONS_TOTAL = Counter(
    "vocpass_pocketbase_operations_total",
    "PocketBase 操作次數",
    ["collection", "operation", "status"],  # operation: create/read/update/delete
)

PB_OPERATION_DURATION_SECONDS = Histogram(
    "vocpass_pocketbase_operation_duration_seconds",
    "PocketBase 操作耗時（秒）",
    ["collection", "operation"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 3.0, 10.0],
)

USER_OPERATIONS_TOTAL = Counter(
    "vocpass_user_operations_total",
    "使用者操作次數",
    ["operation"],  # get / update / avatar
)

CURRICULUM_SHARE_TOTAL = Counter(
    "vocpass_curriculum_share_total",
    "課表分享次數",
    ["status"],  # shared / private
)

RESTAURANT_OPERATIONS_TOTAL = Counter(
    "vocpass_restaurant_operations_total",
    "餐廳功能操作次數",
    ["operation"],  # list / evaluate_get / evaluate_post / create
)

REPORT_TOTAL = Counter(
    "vocpass_report_total",
    "檢舉次數",
)

NOTIFICATION_TOTAL = Counter(
    "vocpass_notification_total",
    "推播通知次數",
    ["status"],  # success / failed
)

import os as _os

APP_INFO = Info(
    "vocpass_app",
    "應用程式基本資訊",
)
APP_INFO.info({
    "version": "1.0.0",
    "framework": "fastapi",
    "instance": _os.environ.get("INSTANCE_ID", "default"),
})

SCHOOLS_LOADED = Gauge(
    "vocpass_schools_loaded_total",
    "已載入的學校設定總數",
)

SCHOOLS_BY_VERSION = Gauge(
    "vocpass_schools_by_version_total",
    "各 API 版本支援的學校數",
    ["api_version"],
)
