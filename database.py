import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()

# If DATABASE_URL exists (on Streamlit Cloud) use Postgres, else use local sqlite
DB_URL = os.getenv("DATABASE_URL", "sqlite:///jawabu.db")
engine = create_engine(DB_URL)

def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(50),
            mpesa_code VARCHAR(20) UNIQUE,
            amount DECIMAL,
            phone VARCHAR(20),
            status VARCHAR(20),
            allocated_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50),
            action VARCHAR(100),
            record_id VARCHAR(100),
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """))
        conn.commit()

def get_engine():
    return engine
