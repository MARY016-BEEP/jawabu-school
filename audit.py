from sqlalchemy import text
from database import get_engine

def log_action(user_id, action, record_id, details):
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO audit_logs (user_id, action, record_id, details)
                VALUES (:u, :a, :r, :d)
            """), {"u": str(user_id), "a": str(action), "r": str(record_id), "d": str(details)})
            conn.commit()
    except Exception as e:
        print(f"Audit log failed: {e}")
