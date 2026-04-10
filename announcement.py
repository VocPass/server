import pocketbase
import asyncio
import os

from utils.send_notification import send_notification

from dotenv import load_dotenv

load_dotenv()

title = "sus"
body = "屁眼派對"

db = pocketbase.PocketBase(os.getenv("PB_URL"))
db.admins.auth_with_password(os.getenv("PB_EMAIL"), os.getenv("PB_PASSWORD"))

users = db.collection("notify").get_full_list()


async def for_all():
    i = 0
    for i in users:
        i += 1
        try:
            await send_notification(title, body, i.apns_token)

        except Exception as e:
            print(f"Error sending notification to {i.id}: {e}")
        print(f"[{i}/{len(users)}]")


async def to_one():
    token = "f51016762d9236c86acc630dbf2bf1670575f7eddc9dc77080ab6977920f0bc1"
    await send_notification(title, body, token)


asyncio.run(to_one())
