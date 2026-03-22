import os
import pocketbase
from dotenv import load_dotenv

load_dotenv()
pb = pocketbase.PocketBase(os.getenv("PB_URL"))

def get_user(token):
    try:
        pb.auth_store.save(token, None)
        record = pb.collection('users').auth_refresh().record
        record.avatar = pb.get_file_url(record, record.avatar)
        return record
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None