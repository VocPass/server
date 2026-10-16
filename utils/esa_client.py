"""ESA -> HSA 單一登入。Cookie 依網域及路徑隔離，且不跨使用者共用 session。"""

import asyncio
from contextlib import asynccontextmanager
from http.cookies import CookieError, SimpleCookie

import aiohttp
from bs4 import BeautifulSoup
from yarl import URL

from utils import metrics as m
from utils.logger import log_school_fetch


class EsaError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def update_response_cookies(jar, response):
    # ESA deletes and then reissues `hsa` in the same response. Batch parsing in
    # aiohttp can retain the deletion's expiry; apply each Set-Cookie in order.
    for item in (*response.history, response):
        for header in item.headers.getall("Set-Cookie", []):
            cookie = SimpleCookie()
            try:
                cookie.load(header)
            except CookieError:
                continue
            jar.update_cookies(cookie, response_url=item.url)


class EsaClient:
    def __init__(self, session, school, school_name):
        self.session = session
        self.school = school
        self.school_name = school_name
        self.student_name = ""

    async def fetch(self, base, path, endpoint, data=None):
        method = "POST" if data is not None else "GET"
        start = asyncio.get_running_loop().time()
        code, size = 0, 0
        try:
            async with self.session.request(method, base + path, data=data) as response:
                update_response_cookies(self.session.cookie_jar, response)
                code = response.status
                body = await response.text(encoding="utf-8")
                size = len(body.encode("utf-8"))
                if code != 200:
                    raise EsaError(502, "Failed to fetch original data.")
                if "請重新登入" in body or "location.replace(\"https://esa.ntpc.edu.tw/\")" in body:
                    raise EsaError(403, "School session expired. Please log in again.")
                return body
        except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeDecodeError) as exc:
            raise EsaError(502, "Failed to fetch original data.") from exc
        finally:
            duration = asyncio.get_running_loop().time() - start
            m.SCHOOL_FETCH_TOTAL.labels(school_name=self.school_name, endpoint=endpoint, method=method, status_code=code).inc()
            m.SCHOOL_FETCH_DURATION_SECONDS.labels(school_name=self.school_name, endpoint=endpoint, method=method).observe(duration)
            m.SCHOOL_FETCH_SIZE_BYTES.labels(school_name=self.school_name, endpoint=endpoint).observe(size)
            log_school_fetch(school_name=self.school_name, endpoint=endpoint, method=method,
                             status_code=code, duration_ms=duration * 1000, response_size=size)

    async def get(self, path, endpoint):
        return await self.fetch(self.school["logined_api"], path, endpoint)

    async def post(self, path, endpoint, data):
        return await self.fetch(self.school["logined_api"], path, endpoint, data)

    async def bootstrap(self):
        # Opening this ESA page issues the domain-scoped `hsa` SSO cookie.
        await self.fetch(self.school["api"], self.school["cookie"]["entry"], "sso_entry")
        if "hsa" not in self.session.cookie_jar.filter_cookies(URL(self.school["logined_api"])):
            raise EsaError(403, "ESA session expired or no high-school access. Please log in again.")
        await self.get(self.school["cookie"]["portal"], "sso_portal")
        portal = await self.get(self.school["cookie"]["profile"], "sso_profile")
        soup = BeautifulSoup(portal, "html.parser")
        if not soup.find(id="StuAffairs/LoginStu") or not soup.find(id="StuScoreQuery/LoginStu"):
            raise EsaError(403, "No student access to the high-school system.")
        school_name = ""
        for label in soup.find_all("strong"):
            if not isinstance(label.next_sibling, str):
                continue
            if label.get_text(strip=True) == "機關學校：":
                school_name = label.next_sibling.strip()
            elif label.get_text(strip=True) == "使用者名稱：":
                self.student_name = label.next_sibling.strip()
        if school_name != self.school["school_full_name"]:
            raise EsaError(403, "Logged-in school does not match school_name.")

    async def open_system(self, system):
        await self.get(self.school["cookie"][system], f"{system}_login")


@asynccontextmanager
async def open_esa_client(cookies, school, school_name):
    jar = aiohttp.CookieJar()
    # Incoming cookies are from ESA. Never flatten ESA and HSA JSESSIONID cookies.
    jar.update_cookies(cookies, response_url=URL(school["api"]))
    async with aiohttp.ClientSession(cookie_jar=jar, timeout=aiohttp.ClientTimeout(total=30),
                                     headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-TW,zh;q=0.9"}) as session:
        client = EsaClient(session, school, school_name)
        await client.bootstrap()
        yield client
