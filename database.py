from sqlalchemy import create_engine, text
import os
import streamlit as st

def get_engine():
    db_url = os.getenv("DATABASE_URL") or st.secrets.get("DATABASE_URL", "sqlite:///jawabu.db")
    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False})
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)

def init_db():
    engine = get_engine()
    is_postgres = engine.url.drivername.startswith("postgresql")
    id_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    auto_id = lambda name: f"{name} {id_type}"

    with engine.connect() as conn:
        # Clean broken audit table
        try:
            conn.execute(text("DROP TABLE IF EXISTS audit_logs;"))
            conn.commit()
        except: pass

        # Create tables
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS payments (id {id_type}, student_id VARCHAR(50), amount DECIMAL, phone VARCHAR(20), status VARCHAR(20), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS bills (id {id_type}, title VARCHAR(100), amount DECIMAL, category VARCHAR(50), paid_by VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS audit_logs (id {id_type}, user_id VARCHAR(50), action VARCHAR(50), record_id VARCHAR(50), details TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS fee_structure (id {id_type}, class_group VARCHAR(50), term VARCHAR(20), amount DECIMAL);"))
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS students (id {id_type}, admission_no VARCHAR(20) UNIQUE, full_name VARCHAR(100), class_group VARCHAR(50), term VARCHAR(20), parent_phone VARCHAR(20), total_fee DECIMAL, paid_amount DECIMAL DEFAULT 0, balance DECIMAL, status VARCHAR(20) DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS marks (id {id_type}, admission_no VARCHAR(20), class_name VARCHAR(30), subject VARCHAR(50), score INTEGER, term VARCHAR(20), teacher VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.commit()

        # ---- FIX FOR REPEATING FEES ----
        # 1. Delete duplicates, keep only 1 per class+term
        try:
            if is_postgres:
                conn.execute(text("""
                    DELETE FROM fee_structure a USING fee_structure b
                    WHERE a.id > b.id AND a.class_group = b.class_group AND a.term = b.term;
                """))
            else:
                conn.execute(text("""
                    DELETE FROM fee_structure WHERE id NOT IN (
                        SELECT MIN(id) FROM fee_structure GROUP BY class_group, term
                    );
                """))
            conn.commit()
        except Exception as e:
            print(f"Clean duplicates failed: {e}")

        # 2. Insert ONLY if not exists
        fees = [
            ("Playgroup","Term 1",5000), ("PP1 & PP2","Term 1",7000), ("Grade 1 to 6","Term 1",9000), ("Grade 7 to 9","Term 1",12000),
            ("Playgroup","Term 2",5000), ("PP1 & PP2","Term 2",7000), ("Grade 1 to 6","Term 2",9000), ("Grade 7 to 9","Term 2",12000),
            ("Playgroup","Term 3",4000), ("PP1 & PP2","Term 3",5000), ("Grade 1 to 6","Term 3",7000), ("Grade 7 to 9","Term 3",10000),
        ]
        for c,t,a in fees:
            try:
                # Check if exists
                exists = conn.execute(text("SELECT id FROM fee_structure WHERE class_group=:c AND term=:t"), {"c":c,"t":t}).scalar()
                if not exists:
                    conn.execute(text("INSERT INTO fee_structure (class_group, term, amount) VALUES (:c,:t,:a)"), {"c":c,"t":t,"a":a})
                    conn.commit()
            except: pass
