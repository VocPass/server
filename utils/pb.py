import os
import pocketbase
from dotenv import load_dotenv

load_dotenv()


def get_user(token):
    pb = pocketbase.PocketBase(os.getenv("PB_URL"))
    try:
        pb.auth_store.save(token, None)
        record = pb.collection('users').auth_refresh().record
        record.avatar = pb.get_file_url(record, record.avatar)
        return record
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None
    

def share_curriculum(user_token, curriculum_data, status):
    pb = pocketbase.PocketBase(os.getenv("PB_URL"))
    pb.auth_store.save(user_token, None)
    record = pb.collection('users').auth_refresh().record
    
    pb.collection('users').update(record.id, {
        "curriculum": curriculum_data,
        "curriculum_status": bool(status)
    })

def set_user(token):
    pb = pocketbase.PocketBase(os.getenv("PB_URL"))
    pb.auth_store.save(token, None)
    return pb


def set_user_school(user_token, school):
    pb = pocketbase.PocketBase(os.getenv("PB_URL"))
    pb.auth_store.save(user_token, None)
    record = pb.collection('users').auth_refresh().record
    pb.collection('users').update(record.id, {
        "school": school
    })



# 刪除非a-zA-Z0-9_.
def sanitize_str(text):
    return "".join(c for c in text if c.isalnum() or c in (".", "_","-","(",")"," ")).rstrip()
