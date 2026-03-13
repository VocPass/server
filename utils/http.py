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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "frame",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
        }

    async def get(self, url, cookies):
        async with aiohttp.ClientSession(
            cookies=cookies, headers=self.headers
        ) as session:
            async with session.get(url) as resp:
                body = await resp.text(encoding="big5")
                if resp.status != 200:
                    return ResponseModel(code=resp.status, message="Failed to fetch data.", data=body)

                try:
                    parsed = json.loads(body)
                except json.JSONDecodeError:
                    return ResponseModel(code=200, message="Success.", data=body)
                except Exception:
                    return ResponseModel(code=500, message="Failed to parse response.", data=body)

                return ResponseModel(code=200, message="Success.", data=parsed)
