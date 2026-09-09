import streamlit as st
from sqlalchemy import text
from database import get_engine
import datetime

# --- USERS FOR JAWABU LEARNING CENTER ---
USERS = {
    "reception": {"password": "reception123", "role": "reception"},
    "teacher": {"password": "teacher123", "role": "teacher"},
    "accountant": {"password": "accountant123", "role": "accountant"},
    "admin": {"password": "admin123", "role": "admin"},
    "mary": {"password": "mary123", "role": "admin"},
}

def check_login(username, password):
    username = username.lower().strip()
    if username in USERS and USERS[username]["password"] == password:
        return {"username": username, "role": USERS[username]["role"]}
    return None

def log_action(user_id, action, record_id="", details=""):
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO audit_logs (user_id, action, record_id, details)
                VALUES (:u, :a, :r, :d)
            """), {"u": user_id, "a": action, "r": record_id, "d": details})
            conn.commit()
    except:
        pass
