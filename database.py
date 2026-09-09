from sqlalchemy import create_engine, text
import os
import streamlit as st

def get_engine():
    db_url = os.getenv("DATABASE_URL") or st.secrets.get("DATABASE_URL", "sqlite:///jawabu.db")
    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False})
    return create_engine(db_url)

def init_db():
    engine = get_engine()
    with engine.connect() as conn:
        # Payments
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id VARCHAR(50),
                amount DECIMAL,
                phone VARCHAR(20),
                status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        # Bills
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(100), amount DECIMAL, category VARCHAR(50),
                paid_by VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        # Audit
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(50), action VARCHAR(50),
                target_id VARCHAR(50), details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        # NEW: Fee Structure
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fee_structure (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_group VARCHAR(50),
                term VARCHAR(20),
                amount DECIMAL,
                UNIQUE(class_group, term)
            );
        """))
        # NEW: Students
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_no VARCHAR(20) UNIQUE,
                full_name VARCHAR(100),
                class_group VARCHAR(50),
                term VARCHAR(20),
                parent_phone VARCHAR(20),
                total_fee DECIMAL,
                paid_amount DECIMAL DEFAULT 0,
                balance DECIMAL,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()

        # Insert your fees automatically
        fees = [
            ("Playgroup","Term 1",5000), ("PP1 & PP2","Term 1",7000), ("Grade 1 to 6","Term 1",9000), ("Grade 7 to 9","Term 1",12000),
            ("Playgroup","Term 2",5000), ("PP1 & PP2","Term 2",7000), ("Grade 1 to 6","Term 2",9000), ("Grade 7 to 9","Term 2",12000),
            ("Playgroup","Term 3",4000), ("PP1 & PP2","Term 3",5000), ("Grade 1 to 6","Term 3",7000), ("Grade 7 to 9","Term 3",10000),
        ]
        for c,t,a in fees:
            try:
                conn.execute(text("INSERT INTO fee_structure (class_group, term, amount) VALUES (:c,:t,:a)"), {"c":c,"t":t,"a":a})
                conn.commit()
            except: pass
