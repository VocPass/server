from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="templates")

SITE_URL = "https://vocpass.com"
ICON_URL = "https://cdn.vocpass.com/iconr.png"
SHARE_IMAGE_URL = "https://cdn.vocpass.com/bg.png"

DEFAULT_META: dict[str, Any] = {
    "title": "VocPass | 高職通用校務查詢系統",
    "description": (
        "VocPass 是專為高職生打造的通用校務查詢系統，支援課表、成績、"
        "缺曠、獎懲、桌布與 When2Meet 約時間工具。"
    ),
    "keywords": "VocPass, 高職, 校務查詢, 課表, 成績, 缺曠, 獎懲, When2Meet, 桌布",
    "robots": "index, follow",
    "type": "website",
    "path": "/",
    "canonical": True,
    "structured_data": False,
}

PAGE_META: dict[str, dict[str, Any]] = {
    "index": {
        "path": "/",
        "structured_data": True,
    },
    "roc": {
        "title": "VocPass｜高級中等學校校務資料便民查詢服務網",
        "description": "VocPass 高級中等學校校務資料便民查詢服務網，提供課表、成績、缺曠、獎懲、支援學校與服務狀態資訊。",
        "path": "/roc",
        "structured_data": True,
    },
    "404": {
        "title": "404 | VocPass",
        "description": "找不到你要瀏覽的 VocPass 頁面。回到首頁查看校務查詢、課表、成績、缺曠、桌布與約時間工具。",
        "robots": "noindex, follow",
        "path": "/404",
        "canonical": False,
    },
    "apply": {
        "title": "VocPass | 新學校申請",
        "description": "申請新增學校至 VocPass 支援清單，協助高職學生查詢課表、成績、缺曠與獎懲資料。",
        "path": "/apply",
    },
    "apply_admin": {
        "title": "VocPass | 論壇版主申請",
        "description": "申請成為 VocPass 校園論壇版主，協助維護討論品質、處理回報並建立友善校園社群。",
        "path": "/apply/admin",
    },
    "auth": {
        "title": "VocPass | 登入",
        "description": "使用 Google 或 Discord 登入 VocPass，管理帳號資料並在 App 與網頁服務間安全銜接。",
        "robots": "noindex, follow",
        "path": "/auth",
    },
    "login": {
        "title": "VocPass | 登入",
        "description": "登入 VocPass 以使用校務查詢與帳號相關服務。",
        "robots": "noindex, follow",
        "path": "/api/demo/login",
    },
    "me": {
        "title": "VocPass | 我的帳號",
        "description": "查看與管理你的 VocPass 帳號資料、學校設定與課表共享狀態。",
        "robots": "noindex, follow",
        "path": "/me",
    },
    "user": {
        "title": "VocPass | 個人資料",
        "description": "查看 VocPass 使用者公開資料與共享課表，快速了解同學的校園課表資訊。",
        "type": "profile",
        "path": "/@{username}",
    },
    "privacy-policy": {
        "title": "隱私權政策 | VocPass",
        "description": "VocPass 隱私權政策說明個人資料、錯誤紀錄與服務資料的收集、使用與保護方式。",
        "type": "article",
        "path": "/privacy-policy",
    },
    "disclaimer": {
        "title": "免責聲明 | VocPass",
        "description": "VocPass 免責聲明說明非官方服務性質、資料來源限制與使用者應注意事項。",
        "type": "article",
        "path": "/disclaimer",
    },
    "creator-policy": {
        "title": "創作者政策 | VocPass",
        "description": "VocPass 創作者政策說明創作者內容、授權範圍、權利義務與平台使用規則。",
        "type": "article",
        "path": "/creator-policy",
    },
    "terms-of-use": {
        "title": "內容使用條款 | VocPass",
        "description": "VocPass 內容使用條款說明平台內容、創作者作品、授權限制與使用者責任。",
        "type": "article",
        "path": "/terms-of-use",
    },
    "community-guidelines": {
        "title": "社群規範 | VocPass",
        "description": "VocPass 社群規範說明論壇討論、內容發布、檢舉與違規處理原則，協助建立友善校園交流空間。",
        "type": "article",
        "path": "/community-guidelines",
    },
    "font": {
        "title": "字體預覽 | VocPass",
        "description": "VocPass 字體預覽工具，用於檢視不同中文字型在校園內容中的呈現效果。",
        "robots": "noindex, nofollow",
        "path": "/font",
    },
    "w2m_redirect": {
        "title": "開啟 VocPass | When2Meet",
        "description": "開啟 VocPass App 查看 When2Meet 活動，或改用網頁版檢視大家的可用時段。",
        "robots": "noindex, follow",
        "path": "/w2m/{event_id}",
    },
    "w2m_view": {
        "title": "VocPass | When2Meet",
        "description": "在網頁中查看 VocPass When2Meet 活動，登入後可填寫可用時段並比較大家都有空的時間。",
        "robots": "noindex, follow",
        "path": "/w2m/view/{event_id}",
    },
}


class _SafeContext(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _absolute_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        return path
    return f"{SITE_URL}{path}"


def build_page_meta(page_key: str, **context: Any) -> dict[str, Any]:
    meta = {**DEFAULT_META, **PAGE_META.get(page_key, {})}
    if context.get("canonical_path"):
        meta["path"] = context["canonical_path"]

    path = meta.get("path")
    if isinstance(path, str):
        path = path.format_map(_SafeContext(context))

    canonical_url = _absolute_url(path) if meta.get("canonical", True) else None
    og_url = canonical_url or SITE_URL

    structured_data = None
    if meta.get("structured_data"):
        structured_data = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": "VocPass",
            "applicationCategory": "EducationApplication",
            "operatingSystem": "iOS, Android, macOS",
            "description": meta["description"],
            "url": SITE_URL,
            "image": SHARE_IMAGE_URL,
            "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "TWD",
            },
        }

    return {
        **meta,
        "canonical_url": canonical_url,
        "og_url": og_url,
        "icon_url": ICON_URL,
        "share_image_url": SHARE_IMAGE_URL,
        "structured_data": structured_data,
    }


def render_page(
    request: Request,
    name: str,
    page_key: str,
    status_code: int = 200,
    **context: Any,
):
    template_context = {
        **context,
        "request": request,
        "page_key": page_key,
        "page_meta": build_page_meta(page_key, **context),
    }
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=template_context,
        status_code=status_code,
    )
