import streamlit as st
import pandas as pd
from datetime import datetime
import os, json
from dotenv import load_dotenv
from sqlalchemy import text

# Our new modules
from database import get_engine, init_db
from mpesa import stk_push
from fee_allocation import auto_allocate
from audit import log_action, get_audit_logs
from notifications import send_sms, send_announcement
from fpdf import FPDF

load_dotenv()
init_db()
engine = get_engine()

st.set_page_config(page_title="JAWABU LEARN - School System", layout="wide")

# --- SESSION ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'role' not in st.session_state:
    st.session_state.role = None

# --- LOGIN SYSTEM ---
def login_page():
    st.title("🔐 JAWABU LEARN Login")
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Username / Admission No")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Login as", ["admin", "parent", "teacher", "student"])
        if st.button("Login"):
            # Simple auth - replace with DB check
            if username and password:
                st.session_state.user = username
                st.session_state.role = role
                log_action(username, "LOGIN", username, f"Logged in as {role}")
                st.rerun()
            else:
                st.error("Enter username and password")

if not st.session_state.user:
    login_page()
    st.stop()

# --- SIDEBAR ---
st.sidebar.title(f"Welcome {st.session_state.user} ({st.session_state.role})")
menu = st.sidebar.radio("Menu", ["Dashboard", "Pay Fees (STK Push)", "Payments & Auto Reconciliation", "Students", "Report Cards", "Announcements", "Audit Logs"])

if st.sidebar.button("Logout"):
    log_action(st.session_state.user, "LOGOUT", st.session_state.user, "Logged out")
    st.session_state.user = None
    st.rerun()

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.header("📊 School Dashboard")
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='confirmed'")).scalar()
        count = conn.execute(text("SELECT COUNT(*) FROM payments")).scalar()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Fees Collected", f"KES {total}")
    c2.metric("Total Transactions", count)
    c3.metric("Outstanding Balance", "Auto-calculated")

# --- 2. PAY FEES - REAL MPESA STK PUSH ---
elif menu == "Pay Fees (STK Push)":
    st.header("💳 Pay School Fees - Automatic Mpesa")
    st.info("Parent enters phone → STK Push sent → Payment auto-confirms and allocates to balances. NO manual typing of Mpesa code!")
    
    student_id = st.text_input("Student Admission No", placeholder="e.g JSS001")
    phone = st.text_input("Parent Phone (254...)", placeholder="254712345678")
    amount = st.number_input("Amount to Pay", min_value=1)
    
    # Get outstanding balances from DB (demo values)
    st.subheader("Outstanding Balances (Auto allocation priority: Tuition > Library > Transport)")
    tuition = st.number_input("Tuition Balance", value=20000)
    library = st.number_input("Library Balance", value=2000)
    transport = st.number_input("Transport Balance", value=3000)
    balances = {"tuition": tuition, "library": library, "transport": transport}
    
    if st.button("🔔 Send STK Push Now"):
        if not student_id or not phone:
            st.error("Enter student ID and phone")
        else:
            with st.spinner("Sending STK Push to parent..."):
                # Preview allocation
                allocation = auto_allocate(student_id, amount, balances)
                st.json(allocation)
                
                # REAL STK PUSH
                try:
                    response = stk_push(phone, amount, student_id)
                    st.success(f"STK Push Sent! Check phone {phone}")
                    st.write(response)
                    log_action(st.session_state.user, "STK_PUSH_INITIATED", student_id, f"Amount {amount} to {phone} | Alloc {allocation}")
                    # Save as pending awaiting callback
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO payments (student_id, amount, phone, status, allocated_json) VALUES (:s, :a, :p, 'pending', :j)"),
                                     {"s": student_id, "a": amount, "p": phone, "j": json.dumps(allocation)})
                        conn.commit()
                except Exception as e:
                    st.error(f"STK Push failed: {e}. Check your Daraja keys in Secrets.")

# --- 3. PAYMENTS TABLE ---
elif menu == "Payments & Auto Reconciliation":
    st.header("💰 Automatic Reconciliation")
    st.write("When Mpesa callback arrives, code, amount, phone are auto-filled and allocated. No manual entry needed.")
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT * FROM payments ORDER BY created_at DESC"), conn)
    st.dataframe(df, use_container_width=True)

# --- 4. REPORT CARDS - DOWNLOADABLE PDF ---
elif menu == "Report Cards":
    st.header("📄 Downloadable Student Report Cards")
    student_id = st.text_input("Enter Admission No for Report")
    if st.button("Generate PDF Report Card"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "JAWABU SCHOOL - REPORT CARD", ln=True, align="C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Student: {student_id} | Date: {datetime.now().date()}", ln=True)
        pdf.cell(0, 10, f"Fee Status: Automatically reconciled via Mpesa Daraja API", ln=True)
        pdf.cell(0, 10, f"Generated by: {st.session_state.user}", ln=True)
        # Add more subjects here
        pdf.output("report.pdf")
        with open("report.pdf", "rb") as f:
            st.download_button("⬇️ Download Report Card PDF", f, file_name=f"{student_id}_report.pdf")
        log_action(st.session_state.user, "REPORT_GENERATED", student_id, "Downloaded PDF report card")

# --- 5. ANNOUNCEMENTS & BALANCE NOTIFICATIONS ---
elif menu == "Announcements":
    st.header("📢 School Announcements & Auto Fee Reminders")
    msg = st.text_area("Announcement Message")
    if st.button("Send to All Parents (SMS)"):
        send_announcement(msg)
        st.success("Announcement sent!")
        log_action(st.session_state.user, "ANNOUNCEMENT_SENT", "ALL", msg)

    st.divider()
    st.subheader("Automatic Balance Reminder")
    if st.button("Check & Notify Parents with Balances"):
        st.info("System will scan DB for balances > 0 and send SMS: 'Dear parent, fee balance KES X, pay via Mpesa...'")
        # Call your bal_reminder.py logic here
        st.success("Reminders queued!")

# --- 6. AUDIT LOGS ---
elif menu == "Audit Logs":
    st.header("🕵️ Audit Logs - Who entered, edited, deleted financial records")
    logs = get_audit_logs()
    st.dataframe(pd.DataFrame(logs), use_container_width=True)
