import aiohttp
import json


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
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

    async def get(self, url, cookies,encoding="big5", data=None):
        async with aiohttp.ClientSession(
            cookies=cookies, headers=self.headers
        ) as session:
            async with session.get(url, data=data) as resp:
                body = await resp.text(encoding=encoding)
                if resp.status != 200:
                    return ResponseModel(
                        code=resp.status, message="Failed to fetch data.", data=body
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

    async def post(self, url, data, cookies,encoding="big5"):
        async with aiohttp.ClientSession(
            cookies=cookies, headers=self.headers
        ) as session:
            async with session.post(url, data=data) as resp:
                try:
                    body = await resp.text(encoding=encoding)
                except UnicodeDecodeError:
                    body = await resp.text(encoding="latin1")
                if resp.status != 200:
                    return ResponseModel(
                        code=resp.status, message="Failed to fetch data.", data=body
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
