from database import get_engine
from sqlalchemy import text
from datetime import datetime

def log_action(user_id, action, record_id, details):
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO audit_logs (user_id, action, record_id, details) VALUES (:u, :a, :r, :d)"),
                     {"u": user_id, "a": action, "r": record_id, "d": details})
        conn.commit()

def get_audit_logs():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100")).mappings().all()
        return list(rows)
