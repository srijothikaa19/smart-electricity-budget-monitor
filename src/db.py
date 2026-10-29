import json, os, sqlite3, uuid
from datetime import datetime, timezone
import settings

DEFAULT_DEVICE = {"decimals": 0, "max_kw": 10.0, "budget": None,
                  "last_reading": None, "last_time": None}

def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()

class Store:
    """Shared logic. Backends implement put/get/update/list_all/list_where."""

    def add_capture(self, device_id, frames_b64, captured_at=None):
        cid = uuid.uuid4().hex
        self.put("captures", cid, {
            "device_id": device_id, "captured_at": captured_at or utcnow_iso(),
            "status": "new", "note": "", "frames": frames_b64})
        return cid

    def new_captures(self, limit=20):
        docs = self.list_where("captures", "status", "new", limit)
        return sorted(docs, key=lambda d: d["captured_at"])

    def finish_capture(self, cid, status, note=""):
        fields = {"status": status, "note": note}
        if os.environ.get("KEEP_FRAMES", "0") != "1":
            fields["frames"] = []          # free space and protect privacy
        self.update("captures", cid, fields)

    def get_device(self, device_id):
        merged = dict(DEFAULT_DEVICE)
        merged.update(self.get("devices", device_id) or {})
        return merged

    def update_device(self, device_id, **fields):
        self.update("devices", device_id, fields)

    def last_accepted(self, device_id):
        d = self.get_device(device_id)
        if d["last_reading"] is None:
            return None
        return {"reading": d["last_reading"],
                "time": datetime.fromisoformat(d["last_time"])}

    def save_reading(self, record):
        self.put("readings", uuid.uuid4().hex, record)

    def save_rejection(self, record):
        self.put("rejections", uuid.uuid4().hex, record)


class LocalStore(Store):
    def __init__(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.execute("CREATE TABLE IF NOT EXISTS docs "
                         "(coll TEXT, id TEXT, data TEXT, PRIMARY KEY (coll, id))")
        self.con.commit()

    def put(self, coll, doc_id, data):
        self.con.execute("INSERT OR REPLACE INTO docs VALUES (?,?,?)",
                         (coll, doc_id, json.dumps(data)))
        self.con.commit()

    def get(self, coll, doc_id):
        row = self.con.execute("SELECT data FROM docs WHERE coll=? AND id=?",
                               (coll, doc_id)).fetchone()
        return json.loads(row[0]) if row else None

    def update(self, coll, doc_id, fields):
        cur = self.get(coll, doc_id) or {}
        cur.update(fields)
        self.put(coll, doc_id, cur)

    def list_all(self, coll, limit=50):
        rows = self.con.execute("SELECT id, data FROM docs WHERE coll=?",
                                (coll,)).fetchall()
        return [dict(json.loads(d), _id=i) for i, d in rows][:limit]

    def list_where(self, coll, field, value, limit=20):
        docs = [d for d in self.list_all(coll, 10**9) if d.get(field) == value]
        return docs[:limit]


class FirestoreStore(Store):
    def __init__(self, key_path):
        import firebase_admin
        from firebase_admin import credentials, firestore
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(key_path))
        self.db = firestore.client()

    def put(self, coll, doc_id, data):
        self.db.collection(coll).document(doc_id).set(data)

    def get(self, coll, doc_id):
        snap = self.db.collection(coll).document(doc_id).get()
        return snap.to_dict() if snap.exists else None

    def update(self, coll, doc_id, fields):
        self.db.collection(coll).document(doc_id).set(fields, merge=True)

    def list_all(self, coll, limit=50):
        return [dict(d.to_dict(), _id=d.id)
                for d in self.db.collection(coll).limit(limit).stream()]

    def list_where(self, coll, field, value, limit=20):
        from google.cloud.firestore_v1.base_query import FieldFilter
        q = (self.db.collection(coll)
             .where(filter=FieldFilter(field, "==", value)).limit(limit))
        return [dict(d.to_dict(), _id=d.id) for d in q.stream()]


def get_store():
    if settings.DB_BACKEND == "firestore":
        return FirestoreStore(settings.FIREBASE_KEY_PATH)
    return LocalStore(settings.LOCAL_DB_PATH)