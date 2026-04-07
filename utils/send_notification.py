import json
import time
import os
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


async def send_notification(title: str, body: str, apns_token: str):
    if not apns_token:
        return

    host = APNS_HOST_SANDBOX if CONFIG["use_sandbox"] else APNS_HOST_PRODUCTION
    url = f"https://{host}/3/device/{apns_token}"

    token = make_jwt_token()
    headers = {
        "authorization": f"bearer {token}",
        "apns-topic": CONFIG["bundle_id"],
        "apns-push-type": "alert",
        "apns-priority": "10",
    }

    payload = {
        "aps": {
            "alert": {
                "title": title,
                "body": body,
            },
            "sound": "default",
        }
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    async with httpx.AsyncClient(http2=True) as client:
        resp = await client.post(url, headers=headers, content=payload_json)

    if resp.status_code == 200:
        NOTIFICATION_TOTAL.labels(status="success").inc()
    else:
        NOTIFICATION_TOTAL.labels(status="failed").inc()
