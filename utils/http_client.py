import aiohttp
import json
import time

from utils.logger import log_school_fetch
from utils import metrics as m


class ResponseModel:
    def __init__(self, code=500, message="Unknown Error.", data=None):
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self):
        return {"code": self.code, "message": self.message, "data": self.data}


class HttpsClient:
    def __init__(self):
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-TW,zh;q=0.9",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

    async def get(
        self,
        url: str,
        cookies,
        encoding: str = "big5",
        data=None,
        school_name: str = "unknown",
        endpoint: str = "unknown",
    ):
        start = time.perf_counter()
        http_status = 0

        try:
            async with aiohttp.ClientSession(
                cookies=cookies, headers=self.headers
            ) as session:
                async with session.get(url, data=data) as resp:
                    http_status = resp.status
                    try:
                        body = await resp.text(encoding=encoding)
                    except UnicodeDecodeError:
                        raw = await resp.read()
                        body = raw.decode(encoding, errors="ignore")

                    response_size = len(body.encode("utf-8", errors="ignore"))
                    duration = time.perf_counter() - start

                    m.SCHOOL_FETCH_TOTAL.labels(
                        school_name=school_name, endpoint=endpoint,
                        method="GET", status_code=http_status,
                    ).inc()
                    m.SCHOOL_FETCH_DURATION_SECONDS.labels(
                        school_name=school_name, endpoint=endpoint, method="GET"
                    ).observe(duration)
                    m.SCHOOL_FETCH_SIZE_BYTES.labels(
                        school_name=school_name, endpoint=endpoint
                    ).observe(response_size)

                    if resp.status != 200:
                        m.SCHOOL_FETCH_ERRORS_TOTAL.labels(
                            school_name=school_name, endpoint=endpoint,
                            error_type=f"http_{http_status}",
                        ).inc()
                        log_school_fetch(
                            school_name=school_name, endpoint=endpoint, method="GET",
                            status_code=http_status, duration_ms=duration * 1000,
                            response_size=response_size, error=f"HTTP {http_status}",
                        )
                        return ResponseModel(
                            code=resp.status, message="Failed to fetch data.", data=body
                        )

                    log_school_fetch(
                        school_name=school_name, endpoint=endpoint, method="GET",
                        status_code=http_status, duration_ms=duration * 1000,
                        response_size=response_size,
                    )

                    try:
                        parsed = json.loads(body)
                    except json.JSONDecodeError:
                        return ResponseModel(code=200, message="Success.", data=body)
                    except Exception:
                        return ResponseModel(
                            code=500, message="Failed to parse response.", data=body
                        )

                    return ResponseModel(code=200, message="Success.", data=parsed)

        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            error_msg = str(exc)
            m.SCHOOL_FETCH_ERRORS_TOTAL.labels(
                school_name=school_name, endpoint=endpoint,
                error_type=type(exc).__name__,
            ).inc()
            log_school_fetch(
                school_name=school_name, endpoint=endpoint, method="GET",
                status_code=0, duration_ms=duration_ms, error=error_msg,
            )
            return ResponseModel(code=500, message=error_msg)

    async def post(
        self,
        url: str,
        data,
        cookies,
        encoding: str = "big5",
        school_name: str = "unknown",
        endpoint: str = "unknown",
    ):
        start = time.perf_counter()
        http_status = 0

        try:
            async with aiohttp.ClientSession(
                cookies=cookies, headers=self.headers
            ) as session:
                async with session.post(url, data=data) as resp:
                    http_status = resp.status
                    try:
                        body = await resp.text(encoding=encoding)
                    except UnicodeDecodeError:
                        body = await resp.text(encoding="cp950")

                    response_size = len(body.encode("utf-8", errors="ignore"))
                    duration = time.perf_counter() - start

                    m.SCHOOL_FETCH_TOTAL.labels(
                        school_name=school_name, endpoint=endpoint,
                        method="POST", status_code=http_status,
                    ).inc()
                    m.SCHOOL_FETCH_DURATION_SECONDS.labels(
                        school_name=school_name, endpoint=endpoint, method="POST"
                    ).observe(duration)
                    m.SCHOOL_FETCH_SIZE_BYTES.labels(
                        school_name=school_name, endpoint=endpoint
                    ).observe(response_size)

                    if resp.status != 200:
                        m.SCHOOL_FETCH_ERRORS_TOTAL.labels(
                            school_name=school_name, endpoint=endpoint,
                            error_type=f"http_{http_status}",
                        ).inc()
                        log_school_fetch(
                            school_name=school_name, endpoint=endpoint, method="POST",
                            status_code=http_status, duration_ms=duration * 1000,
                            response_size=response_size, error=f"HTTP {http_status}",
                        )
                        return ResponseModel(
                            code=resp.status, message="Failed to fetch data.", data=body
                        )

                    log_school_fetch(
                        school_name=school_name, endpoint=endpoint, method="POST",
                        status_code=http_status, duration_ms=duration * 1000,
                        response_size=response_size,
                    )

                    try:
                        parsed = json.loads(body)
                    except json.JSONDecodeError:
                        return ResponseModel(code=200, message="Success.", data=body)
                    except Exception:
                        return ResponseModel(
                            code=500, message="Failed to parse response.", data=body
                        )

                    return ResponseModel(code=200, message="Success.", data=parsed)

        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            error_msg = str(exc)
            m.SCHOOL_FETCH_ERRORS_TOTAL.labels(
                school_name=school_name, endpoint=endpoint,
                error_type=type(exc).__name__,
            ).inc()
            log_school_fetch(
                school_name=school_name, endpoint=endpoint, method="POST",
                status_code=0, duration_ms=duration_ms, error=error_msg,
            )
            return ResponseModel(code=500, message=error_msg)
