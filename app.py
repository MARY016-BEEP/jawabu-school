import streamlit as st
import pandas as pd
from sqlalchemy import text
from database import get_engine, init_db
from mpesa import stk_push
from audit import log_action
from fpdf import FPDF
from datetime import datetime

init_db()
engine = get_engine()

st.set_page_config(page_title="JAWABU LEARNING CENTRE - Pink", layout="wide")

# --- BABY PINK THEME ---
st.markdown("""
<style>
   .stApp { background-color: #FFF0F6; }
    [data-testid="stSidebar"] { background-color: #FFD6E8!important; border-right: 2px solid #FFB6D9; }
   .stButton > button {
        background-color: #FF8FAB!important; color: white!important;
        border-radius: 25px!important; border: none!important;
        font-weight: bold!important; padding: 10px 25px!important;
    }
    [data-testid="stMetric"] {
        background-color: white; padding: 15px; border-radius: 15px;
        border-left: 5px solid #FF8FAB;
    }
    h1, h2, h3 { color: #C9184A!important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background: linear-gradient(135deg, #FF8FAB 0%, #FFB6D9 100%); padding: 20px; border-radius: 20px; margin-bottom: 20px; text-align: center; color: white;">
    <h1 style="color: white!important; margin:0;">🌸 JAWABU LEARNING CENTRE 🌸</h1>
    <p style="margin:0;">Where Learning Blossoms</p>
</div>
""", unsafe_allow_html=True)

USERS = {
    "director": {"password": "director123", "role": "director"},
    "accountant": {"password": "acc123", "role": "accountant"},
    "reception": {"password": "reception123", "role": "reception"},
    "teacher1": {"password": "teach123", "role": "teacher"},
}

if 'user' not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

def login():
    st.title("🏫 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in USERS and USERS[u]["password"] == p:
            st.session_state.user = u
            st.session_state.role = USERS[u]["role"]
            log_action(u, "LOGIN", u, f"Logged in as {USERS[u]['role']}")
            st.rerun()
        else:
            st.error("Wrong login.HINT: For director-direct, accountant-ac, reception-recept, teacher1-teach")

if not st.session_state.user:
    login()
    st.stop()

role = st.session_state.role
user = st.session_state.user

st.sidebar.success(f"Logged in: {user} ({role})")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ---------- DIRECTOR ----------
if role == "DIRECTOR":
    st.title("🏫 DIRECTOR Dashboard - JAWABU LEARNING CENTER")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏫 Overview", "💰 Fee Collection", "🧾 Bills", "👩‍🏫 Teachers Progress", "🔍 Audit Trail"])

    with tab1:
        st.subheader("Overview")
        # your overview code stays here...

    with tab2:
        st.subheader("Fee Collection")
        # your fee code stays here...

    with tab3:
        st.subheader("Bills")
        # your bills code stays here...

    with tab4:
        st.subheader("Teachers Progress")
        # your teachers progress code stays here...

    with tab5:
        st.subheader("🔍 Audit Trail - Track Every Change")
        st.info("Shows WHO edited WHAT and WHEN")
        try:
            with engine.connect() as conn:
                audit_df = pd.read_sql(text("SELECT user_id as WHO, action as ACTION, record_id as WHAT, details as DETAILS, created_at as WHEN_TIME FROM audit_logs ORDER BY created_at DESC LIMIT 100"), conn)
            if audit_df.empty:
                st.warning("No edits yet. Log starts now.")
            else:
                st.dataframe(audit_df, use_container_width=True)
                csv = audit_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Audit Report", csv, "audit_trail_jlc.csv", "text/csv")
        except Exception as e:
            st.error(f"Audit table not yet created: {e}")

# ---------- ACCOUNTANT ----------
elif role == "accountant":
    st.header("Accountant - Money Flow")
    tab1, tab2, tab3 = st.tabs(["Mpesa Payments", "Record Bills", "Fee Structure"])

    with tab1:
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM payments ORDER BY created_at DESC"), conn)
        st.dataframe(df, use_container_width=True)

    with tab2:
        title = st.text_input("Bill Title e.g Electricity")
        cat = st.selectbox("Category", ["Utilities","Salaries","Maintenance","Food","Transport","Other"])
        b_amt = st.number_input("Bill Amount", min_value=1, key="bill")
        if st.button("Save Bill"):
            with engine.connect() as conn:
                conn.execute(text("INSERT INTO bills (title, amount, category, paid_by) VALUES (:t,:a,:c,:p)"), {"t":title,"a":b_amt,"c":cat,"p":user})
                conn.commit()
            st.success("Bill recorded!")

    with tab3:
        with engine.connect() as conn:
            df_fees = pd.read_sql(text("SELECT * FROM fee_structure ORDER BY term, class_group"), conn)
        st.dataframe(df_fees, use_container_width=True)

# ---------- RECEPTION ----------
elif role == "reception":
    st.header("Reception - Student Admission")
    st.info("Rule: Student gets Admission Number ONLY after paying 50% of term fee")

    with engine.connect() as conn:
        fee_df = pd.read_sql(text("SELECT * FROM fee_structure"), conn)

    class_choice = st.selectbox("Select Class Group", ["Playgroup","PP1 & PP2","Grade 1 to 6","Grade 7 to 9"])
    term_choice = st.selectbox("Select Term", ["Term 1","Term 2","Term 3"])

    with engine.connect() as conn:
        total_fee = conn.execute(text("SELECT amount FROM fee_structure WHERE class_group=:c AND term=:t"), {"c":class_choice,"t":term_choice}).scalar() or 0

    st.metric(f"Full Fee for {class_choice} - {term_choice}", f"KES {total_fee}")
    min_required = total_fee * 0.5
    st.metric("Minimum to Admit (50%)", f"KES {min_required}")

    with st.form("admit_form"):
        name = st.text_input("Student Full Name")
        phone = st.text_input("Parent Phone 254...")
        adm_no = st.text_input("Admission No e.g JLC/2025/001")
        paid_now = st.number_input("Amount Being Paid Now", min_value=0)
        submit = st.form_submit_button("Admit Student")
        if submit:
            if paid_now < min_required:
                st.error(f"FAILED! Paid {paid_now} is less than minimum {min_required}. Cannot admit.")
            else:
                balance = total_fee - paid_now
                with engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO students (admission_no, full_name, class_group, term, parent_phone, total_fee, paid_amount, balance, status)
                        VALUES (:a,:n,:c,:t,:p,:tf,:pa,:b,'admitted')
                    """), {"a":adm_no,"n":name,"c":class_choice,"t":term_choice,"p":phone,"tf":total_fee,"pa":paid_now,"b":balance})
                    conn.execute(text("INSERT INTO payments (student_id, amount, phone, status) VALUES (:s,:amt,:ph,'confirmed')"), {"s":adm_no,"amt":paid_now,"ph":phone})
                    conn.commit()
                st.success(f"Admitted! {name} | Admission: {adm_no} | Balance: KES {balance}")

    with engine.connect() as conn:
        stud_df = pd.read_sql(text("SELECT * FROM students ORDER BY created_at DESC"), conn)
    st.dataframe(stud_df, use_container_width=True)

# ---------- TEACHER - CBC ----------
else:
    st.header("Teacher - CBC Academics")
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

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS marks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_no VARCHAR(20), class_name VARCHAR(30),
                subject VARCHAR(50), score INTEGER, term VARCHAR(20),
                teacher VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()

    tab1, tab2 = st.tabs(["Enter Marks", "View Report Total & Mean"])
    with tab1:
        with engine.connect() as conn:
            students = pd.read_sql(text("SELECT admission_no, full_name, class_group FROM students WHERE status='admitted'"), conn)
        if students.empty:
            st.warning("No admitted students yet. Reception must admit first.")
        else:
            selected_adm = st.selectbox("Select Student", students['admission_no'].tolist())
            student_info = students[students['admission_no']==selected_adm].iloc[0]
            st.info(f"Student: {student_info['full_name']} | Group: {student_info['class_group']}")
            if student_info['class_group'] in ["Playgroup","PP1 & PP2"]:
                subjects = CBC_SUBJECTS[student_info['class_group']]
                exact_class = student_info['class_group']
            else:
                exact_class = st.selectbox("Exact Class", ["Grade 1","Grade 2","Grade 3","Grade 4","Grade 5","Grade 6"] if student_info['class_group']=="Grade 1 to 6" else ["Grade 7","Grade 8","Grade 9"])
                subjects = CBC_SUBJECTS[student_info['class_group']][exact_class]
            term = st.selectbox("Term", ["Term 1","Term 2","Term 3"])
            scores = {}
            cols = st.columns(2)
            for i, subj in enumerate(subjects):
                with cols[i%2]:
                    scores[subj] = st.number_input(f"{subj} (0-100)", 0, 100, key=f"{subj}_{selected_adm}")
            if st.button("Save All Marks"):
                with engine.connect() as conn:
                    conn.execute(text("DELETE FROM marks WHERE admission_no=:a AND term=:t"), {"a":selected_adm,"t":term})
                    for subj, sc in scores.items():
                        conn.execute(text("INSERT INTO marks (admission_no, class_name, subject, score, term, teacher) VALUES (:adm,:cls,:subj,:sc,:term,:teach)"), {"adm":selected_adm,"cls":exact_class,"subj":subj,"sc":sc,"term":term,"teach":user})
                    conn.commit()
                st.success(f"Saved {len(subjects)} subjects!")

    with tab2:
        search_adm = st.text_input("Enter Admission No to View Report", key="rep")
        search_term = st.selectbox("Term for Report", ["Term 1","Term 2","Term 3"], key="repterm")
        if search_adm:
            with engine.connect() as conn:
                marks_df = pd.read_sql(text("SELECT subject, score FROM marks WHERE admission_no=:a AND term=:t"), conn, params={"a":search_adm,"t":search_term})
            if marks_df.empty:
                st.warning("No marks found")
            else:
                total = marks_df['score'].sum()
                mean = total / len(marks_df)
                def get_grade(m):
                    if m >= 80: return "Exceeding Expectation (EE)"
                    elif m >= 60: return "Meeting Expectation (ME)"
                    elif m >= 40: return "Approaching Expectation (AE)"
                    else: return "Below Expectation (BE)"
                c1,c2,c3 = st.columns(3)
                c1.metric("Total Marks", f"{total}/{len(marks_df)*100}")
                c2.metric("Mean Score", f"{mean:.1f}%")
                c3.metric("Overall Grade", get_grade(mean))
                st.dataframe(marks_df, use_container_width=True)
               # --- MPESA CALLBACK - Makes parent payment auto-reflect in Accounts ---
from streamlit.web.server.websocket_headers import _get_websocket_headers
# In your main Mpesa payment button, after stk_push:

# Example button you already have:
# if st.button("Pay Fees"):
#    response = stk_push(phone, amount, admission_no)
#    with engine.connect() as conn:
#        conn.execute(text("INSERT INTO payments (student_id, amount, phone, status) VALUES (:s,:a,:p,'pending')"), 
#                     {"s":admission_no,"a":amount,"p":phone})
#        conn.commit()
#    st.info("Check your phone for STK Push - Enter PIN")

# Then Safaricom will call your callback URL: https://yourdomain.com/callback
# That callback should run:
# UPDATE payments SET status='confirmed' WHERE phone=:phone AND amount=:amount
# UPDATE students SET paid_amount = paid_amount + :amount, balance = total_fee - paid_amount WHERE admission_no=:admission_no
