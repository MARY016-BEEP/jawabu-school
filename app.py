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
    "reception": {"password": "reception123", "role": "reception"},
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
st.divider()
    st.subheader("👥 All Admitted Students (Reception Data)")
    with engine.connect() as conn:
        all_students = pd.read_sql(text("SELECT * FROM students"), conn)
    st.dataframe(all_students, use_container_width=True)
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
        tab1, tab2, tab3, tab4 = st.tabs(["Mpesa Flow", "Record Bills", "Fee Structure Setup", "Audit Logs"])

# ... inside tab3:
with tab3:
    st.subheader("Set Fees per Class per Term")
    with engine.connect() as conn:
        df_fees = pd.read_sql(text("SELECT * FROM fee_structure ORDER BY term, class_group"), conn)
    st.dataframe(df_fees, use_container_width=True)
    st.write("To edit: Go to database or tell me new amounts")

# ================= TEACHER VIEW =================
# ================= TEACHER VIEW - CBC CURRICULUM =================
elif role == "teacher":
    st.header("👩‍🏫 TEACHER - CBC Academics")

    # CBC SUBJECTS PER CLASS - Kenya
    CBC_SUBJECTS = {
        "Playgroup": ["Language Activities", "Mathematical Activities", "Environmental Activities", "Psychomotor & Creative", "Religious Activities"],
        "PP1 & PP2": ["Language Activities", "Mathematical Activities", "Environmental Activities", "Psychomotor & Creative", "Religious Activities"],
        "Grade 1 to 6": {
            "Grade 1": ["English", "Kiswahili", "Mathematics", "Environmental Activities", "Creative Arts", "Movement & Craft", "Religious Education"],
            "Grade 2": ["English", "Kiswahili", "Mathematics", "Environmental Activities", "Creative Arts", "Movement & Craft", "Religious Education"],
            "Grade 3": ["English", "Kiswahili", "Mathematics", "Environmental Activities", "Creative Arts", "Movement & Craft", "Religious Education"],
            "Grade 4": ["English", "Kiswahili", "Mathematics", "Science & Technology", "Social Studies", "Creative Arts", "Agriculture", "Religious Education"],
            "Grade 5": ["English", "Kiswahili", "Mathematics", "Science & Technology", "Social Studies", "Creative Arts", "Agriculture", "Religious Education"],
            "Grade 6": ["English", "Kiswahili", "Mathematics", "Science & Technology", "Social Studies", "Creative Arts", "Agriculture", "Religious Education"],
        },
        "Grade 7 to 9": {
            "Grade 7": ["English", "Kiswahili", "Mathematics", "Integrated Science", "Social Studies", "Pre-Technical Studies", "Agriculture & Nutrition", "Creative Arts & Sports", "Religious Education", "Life Skills"],
            "Grade 8": ["English", "Kiswahili", "Mathematics", "Integrated Science", "Social Studies", "Pre-Technical Studies", "Agriculture & Nutrition", "Creative Arts & Sports", "Religious Education", "Life Skills"],
            "Grade 9": ["English", "Kiswahili", "Mathematics", "Integrated Science", "Social Studies", "Pre-Technical Studies", "Agriculture & Nutrition", "Creative Arts & Sports", "Religious Education", "Life Skills"],
        }
    }

    # Create marks table if not exists
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS marks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_no VARCHAR(20),
                class_name VARCHAR(30),
                subject VARCHAR(50),
                score INTEGER,
                term VARCHAR(20),
                teacher VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()

    tab1, tab2 = st.tabs(["📝 Enter Marks Per Subject", "📊 View Report - Total & Mean"])

    with tab1:
        # Get students list from reception
        with engine.connect() as conn:
            students = pd.read_sql(text("SELECT admission_no, full_name, class_group FROM students WHERE status='admitted'"), conn)

        if students.empty:
            st.warning("No admitted students yet. Reception must admit first.")
        else:
            adm_list = students['admission_no'].tolist()
            selected_adm = st.selectbox("Select Student Admission No", adm_list)
            student_info = students[students['admission_no']==selected_adm].iloc[0]
            st.info(f"Student: {student_info['full_name']} | Group: {student_info['class_group']}")

            # Determine subjects based on class
            if student_info['class_group'] in ["Playgroup","PP1 & PP2"]:
                subjects = CBC_SUBJECTS[student_info['class_group']]
            else:
                # For Grade groups, let teacher choose exact class
                exact_class = st.selectbox("Select Exact Class",
                    ["Grade 1","Grade 2","Grade 3","Grade 4","Grade 5","Grade 6"] if student_info['class_group']=="Grade 1 to 6" else ["Grade 7","Grade 8","Grade 9"])
                subjects = CBC_SUBJECTS[student_info['class_group']][exact_class]

            term = st.selectbox("Term", ["Term 1","Term 2","Term 3"])

            st.subheader(f"Enter Scores for {selected_adm} - {term}")
            scores = {}
            cols = st.columns(2)
            for i, subj in enumerate(subjects):
                with cols[i%2]:
                    scores[subj] = st.number_input(f"{subj} (0-100)", 0, 100, key=f"{subj}_{selected_adm}")

            if st.button("💾 Save All Marks"):
                with engine.connect() as conn:
                    # delete old marks for this term
                    conn.execute(text("DELETE FROM marks WHERE admission_no=:a AND term=:t"), {"a":selected_adm,"t":term})
                    for subj, sc in scores.items():
                        conn.execute(text("""
                            INSERT INTO marks (admission_no, class_name, subject, score, term, teacher)
                            VALUES (:adm,:cls,:subj,:sc,:term,:teach)
                        """), {"adm":selected_adm,"cls":exact_class if 'exact_class' in locals() else student_info['class_group'],"subj":subj,"sc":sc,"term":term,"teach":user})
                    conn.commit()
                st.success(f"Saved {len(subjects)} subjects for {selected_adm}!")
                log_action(user, "MARKS_SAVED", selected_adm, f"{term} - {len(subjects)} subjects")

    with tab2:
        st.subheader("Report Card - Total, Mean & Grade")
        search_adm = st.text_input("Enter Admission No to View Report", key="report_search")
        search_term = st.selectbox("Select Term for Report", ["Term 1","Term 2","Term 3"], key="report_term")

        if search_adm:
            with engine.connect() as conn:
                marks_df = pd.read_sql(text("SELECT subject, score FROM marks WHERE admission_no=:a AND term=:t"), conn, params={"a":search_adm,"t":search_term})

            if marks_df.empty:
                st.warning("No marks found for this student in this term")
            else:
                total = marks_df['score'].sum()
                mean = total / len(marks_df)

                # CBC Grading
                def get_grade(m):
                    if m >= 80: return "Exceeding Expectation (EE)"
                    elif m >= 60: return "Meeting Expectation (ME)"
                    elif m >= 40: return "Approaching Expectation (AE)"
                    else: return "Below Expectation (BE)"

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Marks", f"{total}/{len(marks_df)*100}")
                c2.metric("Mean Score", f"{mean:.1f}%")
                c3.metric("Overall Grade", get_grade(mean))

                st.dataframe(marks_df, use_container_width=True)

                # PDF Report Card
                if st.button("Generate Pink Report Card PDF"):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_fill_color(255, 214, 232) # baby pink
                    pdf.rect(0,0,210,297,'F')
                    pdf.set_font("Arial","B",18)
                    pdf.cell(0,15,"🌸 JAWABU LEARN - CBC REPORT CARD 🌸", ln=True, align="C")
                    pdf.set_font("Arial","",12)
                    pdf.cell(0,10,f"Admission: {search_adm} | Term: {search_term} | Mean: {mean:.1f}% | Grade: {get_grade(mean)}", ln=True, align="C")
                    pdf.ln(10)
                    for _, row in marks_df.iterrows():
                        pdf.cell(0,8,f"{row['subject']}: {row['score']}/100", ln=True)
                    pdf.ln(5)
                    pdf.cell(0,10,f"TOTAL: {total} | MEAN: {mean:.1f}", ln=True)
                    pdf.output("cbc_report.pdf")
                    with open("cbc_report.pdf","rb") as f:
                        st.download_button("📥 Download CBC Report Card", f, file_name=f"{search_adm}_{search_term}_Report.pdf")
