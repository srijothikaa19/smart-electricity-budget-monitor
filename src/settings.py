import os

def load_env(path=".env"):
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

load_env()
DB_BACKEND = os.environ.get("DB_BACKEND", "local")
FIREBASE_KEY_PATH = os.environ.get("FIREBASE_KEY_PATH", "config/firebase_key.json")
LOCAL_DB_PATH = os.environ.get("LOCAL_DB_PATH", "data/local.db")
DEVICE = os.environ.get("DEVICE", "0")
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "15"))