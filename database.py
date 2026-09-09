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
        except:
            pass

        # 1. STUDENTS TABLE - WITH NEW COLUMNS YOU ASKED
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS students (
                id {id_type},
                admission_no VARCHAR(50) UNIQUE,
                full_name VARCHAR(100),
                gender VARCHAR(10),
                dob DATE,
                class_group VARCHAR(50),
                term VARCHAR(20),
                parent_name VARCHAR(100),
                parent_phone VARCHAR(20),
                total_fee INTEGER DEFAULT 0,
                paid_amount INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Try to add new columns if table already exists (migration)
        for col_sql in [
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS gender VARCHAR(10)",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS dob DATE",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS parent_name VARCHAR(100)",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS balance INTEGER DEFAULT 0"
        ]:
            try:
                conn.execute(text(col_sql))
                conn.commit()
            except:
                pass

        # 2. PAYMENTS
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS payments (
                id {id_type},
                student_id VARCHAR(50),
                amount INTEGER,
                phone VARCHAR(20),
                mpesa_receipt VARCHAR(100),
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 3. FEE STRUCTURE
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS fee_structure (
                id {id_type},
                class_group VARCHAR(50),
                term VARCHAR(20),
                amount INTEGER,
                UNIQUE(class_group, term)
            )
        """))

        # 4. BILLS
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS bills (
                id {id_type},
                description VARCHAR(200),
                amount INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 5. MARKS
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS marks (
                id {id_type},
                student_id VARCHAR(50),
                subject VARCHAR(100),
                term VARCHAR(20),
                score INTEGER,
                teacher_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 6. AUDIT LOGS
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id {id_type},
                user_id VARCHAR(50),
                action VARCHAR(100),
                record_id VARCHAR(100),
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.commit()

    return engine
