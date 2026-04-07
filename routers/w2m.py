from fastapi import APIRouter, Response, Request, status
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from utils.pb import get_user
from datetime import datetime, date, time, timedelta
from utils.send_notification import send_notification

templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["When2Meet"])
limiter = Limiter(key_func=get_remote_address)


def generate_slots(date_str: str) -> list[str]:
    """產生某日期從 00:00 到 23:30 每 30 分鐘一個 slot，格式 'YYYY-MM-DD HH:MM'"""
    d = date.fromisoformat(date_str)
    slots = []
    current = datetime.combine(d, time(0, 0))
    end = datetime.combine(d, time(23, 30))
    while current <= end:
        slots.append(current.strftime("%Y-%m-%d %H:%M"))
        current += timedelta(minutes=30)
    return slots


@router.post("/api/w2m/events", summary="建立 When2Meet 活動")
async def create_event(request: Request, response: Response, item: dict):
    """
    建立活動。

    Body:
    - `title` (str, required)
    - `dates` (list[str], required) — ISO 日期清單，例如 ["2026-04-10", "2026-04-11"]
    - `description` (str, optional)

    需要 Authorization header（Bearer token）。
    """
    token = request.headers.get("Authorization")
    if not token:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}

    user = get_user(token)
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}

    title = item.get("title", "").strip()
    dates = item.get("dates", [])
    description = item.get("description", "")

    if not title:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"code": 400, "message": "title is required", "data": None}

    if not dates or not isinstance(dates, list):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"code": 400, "message": "dates must be a non-empty list", "data": None}

    # 驗證日期格式並產生所有 slots
    try:
        all_slots = []
        for d in dates:
            all_slots.extend(generate_slots(d))
    except ValueError:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "code": 400,
            "message": "Invalid date format, use YYYY-MM-DD",
            "data": None,
        }

    db = request.app.state.pb_client
    record = db.collection("w2m_events").create(
        {
            "title": title,
            "description": description,
            "dates": dates,
            "slots": all_slots,
            "creator": user.id,
        }
    )

    return {"code": 200, "message": "Event created.", "data": {"id": record.id}}


@router.patch("/api/w2m/events/{event_id}", summary="編輯活動日期/標題/描述")
async def edit_event(request: Request, response: Response, event_id: str, item: dict):
    """
    編輯活動，只有 creator 可操作。

    Body（皆為選填，僅傳要改的欄位）:
    - `title` (str)
    - `description` (str)
    - `dates` (list[str]) — 若有改日期，slots 會重新產生，**所有人已填的時段會被清除**

    需要 Authorization header（Bearer token）。
    """
    token = request.headers.get("Authorization")
    if not token:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}

    user = get_user(token)
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}

    db = request.app.state.pb_client

    try:
        event = db.collection("w2m_events").get_one(event_id)
    except Exception:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"code": 404, "message": "Event not found.", "data": None}

    if event.creator != user.id:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {
            "code": 403,
            "message": "Only the creator can edit this event.",
            "data": None,
        }

    update_data = {}

    if "title" in item:
        title = item["title"].strip()
        if not title:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"code": 400, "message": "title cannot be empty", "data": None}
        update_data["title"] = title

    if "description" in item:
        update_data["description"] = item["description"]

    if "dates" in item:
        dates = item["dates"]
        if not dates or not isinstance(dates, list):
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                "code": 400,
                "message": "dates must be a non-empty list",
                "data": None,
            }
        try:
            all_slots = []
            for d in dates:
                all_slots.extend(generate_slots(d))
        except ValueError:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                "code": 400,
                "message": "Invalid date format, use YYYY-MM-DD",
                "data": None,
            }

        update_data["dates"] = dates
        update_data["slots"] = all_slots

    if not update_data:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"code": 400, "message": "No fields to update", "data": None}

    db.collection("w2m_events").update(event_id, update_data)

    return {"code": 200, "message": "Event updated.", "data": None}


@router.get("/api/w2m/events", summary="取得自己的活動列表")
async def list_events(request: Request, response: Response):
    """
    回傳目前登入使用者「建立」或「已填寫時段」的活動清單。

    需要 Authorization header（Bearer token）。
    """
    token = request.headers.get("Authorization")
    if not token:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}

    user = get_user(token)
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}

    db = request.app.state.pb_client

    created = db.collection("w2m_events").get_full_list(
        query_params={
            "filter": f'creator="{user.id}"',
            "sort": "-created",
            "expand": "creator",
        }
    )

    avail_records = db.collection("w2m_availability").get_full_list(
        query_params={"filter": f'user="{user.id}"', "expand": "event,event.creator"}
    )
    created_ids = {r.id for r in created}

    participated_events = [
        r.expand["event"]
        for r in avail_records
        if r.event not in created_ids and r.expand and "event" in r.expand
    ]

    def fmt_creator(evt):
        expanded_creator = evt.expand.get("creator") if evt.expand else None
        if expanded_creator:
            avatar_url = (
                db.get_file_url(expanded_creator, expanded_creator.avatar)
                if expanded_creator.avatar
                else None
            )
            creator_info = {
                "id": expanded_creator.id,
                "name": expanded_creator.name,
                "avatar": avatar_url,
            }
        else:
            creator_info = {"id": evt.creator, "name": None, "avatar": None}
        return {
            "id": evt.id,
            "title": evt.title,
            "description": evt.description,
            "dates": evt.dates,
            "creator": creator_info,
        }

    return {
        "code": 200,
        "message": "Success.",
        "data": {
            "created": [fmt_creator(e) for e in created],
            "participated": [fmt_creator(e) for e in participated_events],
        },
    }


@router.get("/api/w2m/events/{event_id}", summary="取得活動與所有成員可用時段")
async def get_event(request: Request, response: Response, event_id: str):
    """
    回傳活動基本資訊與每位成員已選擇的可用時段。

    回傳結構：
    ```json
    {
      "id": "...",
      "title": "...",
      "description": "...",
      "dates": ["2026-04-10"],
      "slots": ["2026-04-10 00:00", ...],
      "availability": {
        "username": ["2026-04-10 09:00", "2026-04-10 09:30"],
        ...
      }
    }
    ```
    """
    db = request.app.state.pb_client
    try:
        event = db.collection("w2m_events").get_one(event_id)
    except Exception:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"code": 404, "message": "Event not found.", "data": None}

    try:
        avail_records = db.collection("w2m_availability").get_full_list(
            query_params={"filter": f'event="{event_id}"', "expand": "user"}
        )
    except Exception:
        avail_records = []

    availability = []
    for rec in avail_records:
        expanded_user = rec.expand.get("user") if rec.expand else None
        if expanded_user:
            avatar_url = (
                db.get_file_url(expanded_user, expanded_user.avatar)
                if expanded_user.avatar
                else None
            )
            user_info = {
                "id": expanded_user.id,
                "name": expanded_user.name,
                "avatar": avatar_url,
            }
        else:
            user_info = {"id": rec.user, "name": None, "avatar": None}
        availability.append({"user": user_info, "slots": rec.slots})

    return {
        "code": 200,
        "message": "Success.",
        "data": {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "dates": event.dates,
            "slots": event.slots,
            "availability": availability,
        },
    }


@router.put("/api/w2m/events/{event_id}/availability", summary="提交自己的可用時段")
async def submit_availability(
    request: Request, response: Response, event_id: str, item: dict
):
    """
    提交或更新自己的可用時段。

    Body:
    - `slots` (list[str]) — 從活動 slots 清單中選出自己有空的項目

    需要 Authorization header（Bearer token）。
    """
    token = request.headers.get("Authorization")
    if not token:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}

    user = get_user(token)
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}

    slots = item.get("slots", [])
    if not isinstance(slots, list):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"code": 400, "message": "slots must be a list", "data": None}

    db = request.app.state.pb_client

    try:
        event = db.collection("w2m_events").get_one(event_id)
    except Exception:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"code": 404, "message": "Event not found.", "data": None}

    valid_slots = [s for s in slots if s in event.slots]

    try:
        existing = db.collection("w2m_availability").get_first_list_item(
            f'event="{event_id}" && user="{user.id}"',
            query_params={"expand": "user"},
        )
        db.collection("w2m_availability").update(existing.id, {"slots": valid_slots})
    except Exception:
        db.collection("w2m_availability").create(
            {
                "event": event_id,
                "user": user.id,
                "slots": valid_slots,
            }
        )
    creator_id = event.creator
    if creator_id != user.id:

        devices = db.collection("notify").get_full_list(
            query_params={"filter": f'user="{creator_id}"'}
        )
        
        for i in devices:
            await send_notification(
                title=f"{event.title} 有新更新！",
                body=f"{user.name} 更新了活動『{event.title}』的可用時段。",
                apns_token=i.apns_token,
            )
    return {"code": 200, "message": "Availability updated.", "data": None}


@router.get("/w2m/{event_id}", summary="跳轉至 app 連結")
async def deeplink_redirect(request: Request, event_id: str):
    """
    透過瀏覽器開啟此 URL，顯示中介頁面後自動跳轉至 vocpass://w2m/<event_id>，
    由 app 攔截並開啟對應的活動頁面。
    """
    return templates.TemplateResponse(
        "w2m_redirect.html",
        {"request": request, "event_id": event_id},
    )
