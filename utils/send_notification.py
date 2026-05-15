import json
import time
import os
import asyncio
import jwt
import httpx

from dotenv import load_dotenv
from utils.metrics import NOTIFICATION_TOTAL

load_dotenv()

CONFIG = {
    "team_id": os.environ.get("team_id"),
    "key_id": os.environ.get("key_id"),
    "key_path": os.environ.get("key_path"),
    "bundle_id": os.environ.get("bundle_id"),
    "use_sandbox": False,
}

APNS_HOST_SANDBOX = "api.sandbox.push.apple.com"
APNS_HOST_PRODUCTION = "api.push.apple.com"


def make_jwt_token():
    with open(CONFIG["key_path"], "r") as f:
        private_key = f.read()
    payload = {
        "iss": CONFIG["team_id"],
        "iat": int(time.time()),
    }
    headers = {
        "alg": "ES256",
        "kid": CONFIG["key_id"],
    }
    return jwt.encode(payload, private_key, algorithm="ES256", headers=headers)


def _get_apns_url(apns_token: str):
    host = APNS_HOST_SANDBOX if CONFIG["use_sandbox"] else APNS_HOST_PRODUCTION
    return f"https://{host}/3/device/{apns_token}"


def _get_apns_headers(token: str):
    return {
        "authorization": f"bearer {token}",
        "apns-topic": CONFIG["bundle_id"],
        "apns-push-type": "alert",
        "apns-priority": "10",
    }


def _get_apns_payload(title: str, body: str):
    return {
        "aps": {
            "alert": {
                "title": title,
                "body": body,
            },
            "sound": "default",
        }
    }


async def _send_notification_with_client(
    client: httpx.AsyncClient,
    headers: dict,
    title: str,
    body: str,
    apns_token: str,
):
    if not apns_token:
        return {"status": "skipped", "status_code": None, "apns_token": apns_token}

    payload_json = json.dumps(_get_apns_payload(title, body), ensure_ascii=False)
    resp = await client.post(
        _get_apns_url(apns_token),
        headers=headers,
        content=payload_json,
    )

    if resp.status_code == 200:
        NOTIFICATION_TOTAL.labels(status="success").inc()
        status = "success"
    else:
        NOTIFICATION_TOTAL.labels(status="failed").inc()
        status = "failed"

    return {
        "status": status,
        "status_code": resp.status_code,
        "apns_token": apns_token,
        "response": resp.text,
    }


async def send_notification(title: str, body: str, apns_token: str):
    if not apns_token:
        return

    headers = _get_apns_headers(make_jwt_token())

    async with httpx.AsyncClient(http2=True) as client:
        result = await _send_notification_with_client(
            client=client,
            headers=headers,
            title=title,
            body=body,
            apns_token=apns_token,
        )

    return result


async def send_notifications(notifications: list[dict], max_concurrency: int = 1000):
    """
    Batch send APNs notifications over one HTTP/2 client.

    notifications example:
    [{"title": "", "body": "", "apns_token": ""}]
    """
    if not notifications:
        return []

    max_concurrency = max(1, max_concurrency)
    semaphore = asyncio.Semaphore(max_concurrency)
    limits = httpx.Limits(
        max_connections=max_concurrency,
        max_keepalive_connections=max_concurrency,
    )
    headers = _get_apns_headers(make_jwt_token())

    async with httpx.AsyncClient(http2=True, limits=limits) as client:
        async def send_one(notification: dict):
            async with semaphore:
                try:
                    return await _send_notification_with_client(
                        client=client,
                        headers=headers,
                        title=notification.get("title", ""),
                        body=notification.get("body", ""),
                        apns_token=notification.get("apns_token", ""),
                    )
                except Exception as exc:
                    NOTIFICATION_TOTAL.labels(status="failed").inc()
                    return {
                        "status": "failed",
                        "status_code": None,
                        "apns_token": notification.get("apns_token", ""),
                        "error": str(exc),
                    }

        return await asyncio.gather(*(send_one(item) for item in notifications))
