import pocketbase
import asyncio
import os
import httpx

from utils.send_notification import send_notification

from dotenv import load_dotenv

load_dotenv()


db = pocketbase.PocketBase(os.getenv("PB_URL"))
db.admins.auth_with_password(os.getenv("PB_EMAIL"), os.getenv("PB_PASSWORD"))

users = db.collection("notify").get_full_list()

TITLE = "即時通知（動態島）已修復"
BODY = "由於昨日更新錯誤，目前課表即時通知功能已修復。另外提醒若需要即時通知（動態島）功能，請重新開啟開關喔"
CONCURRENCY = 100


async def main():
    sem = asyncio.Semaphore(CONCURRENCY)

    async def send(user, client):
        async with sem:
            try:
                await send_notification(TITLE, BODY, user.apns_token, client)
            except Exception as e:
                print(f"Error sending notification to {user.id}: {e}")

    async with httpx.AsyncClient(http2=True) as client:
        await asyncio.gather(*[send(u, client) for u in users])

    print(len(users))


asyncio.run(main())
