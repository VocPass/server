#!/usr/bin/env python3
"""
解析 Google Maps 分享連結：商家名稱 / 評分 / 類別 / 地址 / 座標

用法:
  pip install requests
  python map.py "https://maps.app.goo.gl/Fbsh148eE6AjHFDz6?g_st=ic"
"""
import html
import json
import re
import sys
from urllib.parse import parse_qs, unquote_plus, urlparse

import requests

# Google 只對社群爬蟲回傳含 og 標籤的簡化頁；桌面 UA 會拿到 JS 版，
# og:title 永遠是「Google 地圖」，取不到商家名稱與評分。
HEADERS = {
    "User-Agent": ("facebookexternalhit/1.1 "
                   "(+http://www.facebook.com/externalhit_uatext.php)"),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}
COOKIES = {"CONSENT": "YES+", "SOCS": "CAI"}  # 跳過歐盟同意頁


# ---------- 1. 展開短網址 ----------
def resolve(url: str, s: requests.Session):
    r = s.get(url, allow_redirects=True, timeout=15)
    final = r.url
    if "consent.google" in final:  # 被導到同意頁時，取出原始目標
        cont = parse_qs(urlparse(final).query).get("continue", [None])[0]
        if cont:
            r = s.get(cont, allow_redirects=True, timeout=15)
            final = r.url
    return final, r.text


# ---------- 2. 從長網址解析 ----------
def parse_url(u: str) -> dict:
    info = {}
    p = urlparse(u)
    qs = parse_qs(p.query)

    m = re.search(r"/place/([^/@]+)", p.path)
    if m:
        info["name"] = unquote_plus(m.group(1))
    elif "q" in qs:
        info["query"] = qs["q"][0]

    # !3d!4d 是地點本身座標（比 @ 的地圖中心準）
    m = (re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", u)
         or re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", u))
    if not m and "q" in qs:
        m = re.fullmatch(r"\s*(-?\d+\.\d+),\s*(-?\d+\.\d+)\s*", qs["q"][0])
    if m:
        info["lat"], info["lng"] = float(m.group(1)), float(m.group(2))
    return info


# ---------- 3. 從網頁 HTML 解析 ----------
def _meta(text: str, key: str):
    pat1 = rf'<meta[^>]+(?:property|itemprop|name)="{key}"[^>]*content="([^"]*)"'
    pat2 = rf'<meta[^>]+content="([^"]*)"[^>]*(?:property|itemprop|name)="{key}"'
    m = re.search(pat1, text) or re.search(pat2, text)
    return html.unescape(m.group(1)) if m else None


# 「4.7★(32)」或「4.7 ★」
RATING_RE = re.compile(r"(\d(?:[.,]\d+)?)\s*★\s*(?:\(\s*([\d,.\s]+?)\s*\))?")


def parse_html(text: str) -> dict:
    """og:title 第一段是商家名稱，其餘段落（連同 og:description）
    依內容判斷是評分、類別還是地址 —— Google 會調換兩者的順序。"""
    info = {}
    segments = []
    for key in ("og:title", "og:description"):
        value = _meta(text, key)
        if value:
            segments += [x.strip() for x in value.split("·") if x.strip()]

    if not segments or segments[0] in ("Google Maps", "Google 地圖"):
        return info  # 拿到的是 JS 版頁面，沒有地點資訊

    info["name"] = segments.pop(0)
    for seg in segments:
        m = RATING_RE.search(seg)
        if m:
            info["rating"] = float(m.group(1).replace(",", "."))
            if m.group(2):
                info["rating_count"] = int(re.sub(r"\D", "", m.group(2)))
            continue
        if not set(seg) - set("★☆ "):
            continue  # 只有星星圖示、沒有數字，無法換算成評分
        # 地址必含門牌或郵遞區號；類別（如「中菜館」）則沒有數字
        if re.search(r"\d", seg):
            info.setdefault("address", seg)
        else:
            info.setdefault("category", seg)

    # 座標：og:image 若是靜態地圖，center= 就帶著座標；
    # 否則用 APP_INITIALIZATION_STATE 開頭的 [縮放, 經度, 緯度]
    m = re.search(r"center=(-?\d+\.\d+)%2C(-?\d+\.\d+)", _meta(text, "og:image") or "")
    if m:
        info["lat"], info["lng"] = float(m.group(1)), float(m.group(2))
    else:
        m = re.search(r"APP_INITIALIZATION_STATE=\[\[\[[\d.]+,"
                      r"(-?\d+\.\d+),(-?\d+\.\d+)", text)
        if m:
            info["lng"], info["lat"] = float(m.group(1)), float(m.group(2))
    return info


def parse(url: str, s: requests.Session = None) -> dict:
    s = s or requests.Session()
    s.headers.update(HEADERS)
    s.cookies.update(COOKIES)

    final_url, page = resolve(url, s)
    from_html, from_url = parse_html(page), parse_url(final_url)

    # 名稱/評分/地址以 HTML 為準（網址裡的名稱只是搜尋字串），座標以網址為準
    result = {"resolved_url": final_url}
    for key in ("name", "rating", "rating_count", "category", "address",
                "lat", "lng", "query"):
        order = (from_url, from_html) if key in ("lat", "lng") else (from_html, from_url)
        for source in order:
            if key in source:
                result[key] = source[key]
                break
    return result


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else input("Google Maps 連結: ").strip()
    print(json.dumps(parse(url), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
