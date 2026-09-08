import streamlit as st
import pandas as pd
from sqlalchemy import text
from database import get_engine, init_db
from mpesa import stk_push
from fee_allocation import auto_allocate
from audit import log_action
from notifications import send_sms
from fpdf import FPDF
import json
from datetime import datetime

init_db()
engine = get_engine()

st.set_page_config(page_title="JAWABU LEARN - Role System", layout="wide")
# --- BABY PINK THEME - BEAUTIFUL UI ---
st.markdown("""
<style>
    /* Main background - soft baby pink */
    .stApp {
        background-color: #FFF0F6;
    }
    
    /* Sidebar - deeper baby pink */
    [data-testid="stSidebar"] {
        background-color: #FFD6E8 !important;
        border-right: 2px solid #FFB6D9;
    }
    
    /* All buttons - baby pink */
    .stButton > button {
        background-color: #FF8FAB !important;
        color: white !important;
        border-radius: 25px !important;
        border: none !important;
        font-weight: bold !important;
        padding: 10px 25px !important;
        box-shadow: 0px 4px 10px rgba(255, 143, 171, 0.3) !important;
    }
    .stButton > button:hover {
        background-color: #FF7096 !important;
        transform: scale(1.02);
    }

    /* Metrics cards - white with pink border */
    [data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 15px;
        border-left: 5px solid #FF8FAB;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.05);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: white;
        border-radius: 10px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #FF7096;
    }

    /* Dataframes */
    .stDataFrame {
        border-radius: 15px;
        overflow: hidden;
    }

    /* Headers - pretty */
    h1, h2, h3 {
        color: #C9184A !important;
        font-family: 'Poppins', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# --- PRETTY HEADER WITH LOGO ---
st.markdown("""
<div style="background: linear-gradient(135deg, #FF8FAB 0%, #FFB6D9 100%); padding: 20px; border-radius: 20px; margin-bottom: 20px; text-align: center; color: white;">
    <h1 style="color: white !important; margin:0;">🌸 JAWABU LEARN 🌸</h1>
    <p style="margin:0; font-size:16px;">Where Learning Blossoms - School Management System</p>
</div>
""", unsafe_allow_html=True)
# --- SIMPLE USER DB (later you can move to database) ---
USERS = {
    "director": {"password": "director123", "role": "director"},
    "accountant": {"password": "acc123", "role": "accountant"},
    "teacher1": {"password": "teach123", "role": "teacher"},
}

if 'user' not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

# --- LOGIN ---
def login():
    st.title("🏫 JAWABU LEARN - Secure Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in USERS and USERS[u]["password"] == p:
            st.session_state.user = u
            st.session_state.role = USERS[u]["role"]
            log_action(u, "LOGIN", u, f"Logged in as {USERS[u]['role']}")
            st.rerun()
        else:
            st.error("Wrong username or password. Try: director/director123, accountant/acc123, teacher1/teach123")

if not st.session_state.user:
    login()
    st.stop()

role = st.session_state.role
user = st.session_state.user

st.sidebar.success(f"Logged in: {user} ({role})")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# --- CREATE BILLS TABLE IF NOT EXISTS ---
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS bills (
            id SERIAL PRIMARY KEY,
            title VARCHAR(100),
            amount DECIMAL,
            category VARCHAR(50),
            paid_by VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))
    conn.commit()

# ================= DIRECTOR VIEW =================
if role == "director":
    st.header("👔 DIRECTOR DASHBOARD - Money Overview")

    with engine.connect() as conn:
        total_in = conn.execute(text("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='confirmed'")).scalar() or 0
        total_pending = conn.execute(text("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='pending'")).scalar() or 0
        # For sqlite fallback
        try:
            total_out = conn.execute(text("SELECT COALESCE(SUM(amount),0) FROM bills")).scalar() or 0
            bills_df = pd.read_sql(text("SELECT * FROM bills ORDER BY created_at DESC"), conn)
        except:
            total_out = 0
            bills_df = pd.DataFrame()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Fees IN (Confirmed)", f"KES {total_in}")
    c2.metric("Total Bills OUT (Used)", f"KES {total_out}")
    c3.metric("Balance (IN - OUT)", f"KES {total_in - total_out}")

    st.divider()
    st.subheader("💸 How Money Was Used - Bills & Expenses")
    st.dataframe(bills_df, use_container_width=True)

    st.bar_chart(bills_df.groupby("category")["amount"].sum() if not bills_df.empty else pd.DataFrame())

# ================= ACCOUNTANT VIEW =================
elif role == "accountant":
    st.header("🧾 ACCOUNTANT - Money Flow Monitoring")
    tab1, tab2, tab3 = st.tabs(["Mpesa Payments Flow", "Record Bills / Expenses", "Audit Logs"])

    with tab1:
        st.write("All Mpesa transactions - STK Push auto reconciliation")
        phone = st.text_input("Parent Phone 254...")
        stud = st.text_input("Student Adm No")
        amt = st.number_input("Amount", min_value=1)
        if st.button("Send STK Push"):
            res = stk_push(phone, amt, stud)
            st.success(f"STK sent to {phone}")
            st.json(res)
            with engine.connect() as conn:
                conn.execute(text("INSERT INTO payments (student_id, amount, phone, status) VALUES (:s,:a,:p,'pending')"),
                             {"s":stud,"a":amt,"p":phone})
                conn.commit()

        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM payments ORDER BY created_at DESC"), conn)
        st.dataframe(df, use_container_width=True)

    with tab2:
        st.subheader("Record Money Used (Bills)")
        title = st.text_input("Bill Title e.g Electricity, Water, Salaries")
        cat = st.selectbox("Category", ["Utilities", "Salaries", "Maintenance", "Food", "Transport", "Other"])
        b_amt = st.number_input("Bill Amount", min_value=1, key="bill")
        if st.button("Save Bill - Director will see it"):
            with engine.connect() as conn:
                conn.execute(text("INSERT INTO bills (title, amount, category, paid_by) VALUES (:t,:a,:c,:p)"),
                             {"t":title,"a":b_amt,"c":cat,"p":user})
                conn.commit()
            log_action(user, "BILL_RECORDED", title, f"KES {b_amt} for {cat}")
            st.success("Bill recorded!")

    with tab3:
        with engine.connect() as conn:
            logs = pd.read_sql(text("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100"), conn)
        st.dataframe(logs, use_container_width=True)

# ================= TEACHER VIEW =================
elif role == "teacher":
    st.header("👩‍🏫 TEACHER - Academics Only")
    st.info("You can only see students, marks, and report cards. No money info.")

    tab1, tab2 = st.tabs(["Students & Marks", "Generate Report Card"])
    with tab1:
        st.write("Enter marks, attendance")
        s_id = st.text_input("Admission No")
        subject = st.text_input("Subject")
        marks = st.number_input("Marks /100", 0, 100)
        if st.button("Save Marks"):
            st.success(f"Saved {marks} for {s_id} in {subject}")
            log_action(user, "MARKS_ENTERED", s_id, f"{subject}:{marks}")

    with tab2:
        s_id2 = st.text_input("Student Adm No for Report Card", key="rep")
        if st.button("Generate PDF Report Card"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial","B",16)
            pdf.cell(0,10,"JAWABU SCHOOL - REPORT CARD",ln=True,align="C")
            pdf.set_font("Arial","",12)
            pdf.cell(0,10,f"Student: {s_id2} | Date: {datetime.now().date()}",ln=True)
            pdf.cell(0,10,f"Generated by Teacher: {user}",ln=True)
            pdf.output("report.pdf")
            with open("report.pdf","rb") as f:
                st.download_button("Download Report Card", f, file_name=f"{s_id2}_report.pdf")
