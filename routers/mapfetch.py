"""
抓取中繼站。
"""
from fastapi import APIRouter, Header, HTTPException, Response, status
from urllib.parse import urlparse

import os
import re
import httpx

router = APIRouter(prefix="/mapfetch", tags=["Google Maps 抓取中繼站"])

HEADERS = {
    "User-Agent": ("facebookexternalhit/1.1 "
                   "(+http://www.facebook.com/externalhit_uatext.php)"),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}
COOKIES = {"CONSENT": "YES+", "SOCS": "CAI"}

ALLOWED = (
    re.compile(r"^maps\.app\.goo\.gl$"),
    re.compile(r"^goo\.gl$"),
    re.compile(r"^(www\.)?google\.[a-z.]+$"),
    re.compile(r"^maps\.google\.[a-z.]+$"),
)

TOKEN = os.getenv("MAPFETCH_TOKEN")


@router.get("/", summary="代抓 Google Maps 頁面，回傳原始 HTML")
async def mapfetch(url: str, authorization: str = Header(default="")):
    if TOKEN and authorization != f"Bearer {TOKEN}":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token 不正確")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "只接受 http / https 連結")
    if not any(p.match(parsed.hostname or "") for p in ALLOWED):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"只接受 Google Maps 連結，不支援 {parsed.hostname}")

    async with httpx.AsyncClient(follow_redirects=True, timeout=15,
                                 headers=HEADERS, cookies=COOKIES) as client:
        try:
            r = await client.get(url)
        except httpx.HTTPError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"抓取失敗：{exc}")

    return Response(
        content=r.text,
        media_type="text/html; charset=utf-8",
        headers={"X-Final-Url": str(r.url)},
    )
