import streamlit as st
import pandas as pd
from sqlalchemy import text
import datetime
from database import get_engine, init_db
from auth import check_login, log_action

st.set_page_config(page_title="JAWABU LEARNING CENTER", layout="wide")

engine = get_engine()
init_db()

# --- LOGIN ---
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

if st.session_state.user is None:
    st.title("🏫 JAWABU LEARNING CENTER - Login")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user = check_login(username, password)
            if user:
                st.session_state.user = user["username"]
                st.session_state.role = user["role"]
                st.rerun()
            else:
                st.error("Wrong username/password")
    st.stop()

user = st.session_state.user
role = st.session_state.role
st.sidebar.write(f"Logged in: {user} ({role})")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

# ---------------- RECEPTION ----------------
if role == "reception":
    st.header("Reception - Student Admission - JAWABU LEARNING CENTER")
    st.info("Rule: Auto Admission No + 50% to Admit - Balance RED if not cleared")
    
    tab1, tab2 = st.tabs(["📝 Admit Student (Auto No)", "💰 Record Payment"])

    with tab1:
        st.subheader("📝 Admit New Student")
        
        # Auto Admission No - SIMPLE NO DEF (fixes line 256 error)
        with engine.connect() as conn:
            try:
                count = conn.execute(text("SELECT COUNT(*) FROM students")).scalar() or 0
            except:
                count = 0
            year = datetime.datetime.now().year
            auto_adm_no = f"JLC/{year}/{count+1:03d}"
        
        st.success(f"🔢 Next Admission No (Auto): **{auto_adm_no}**")

        colA, colB = st.columns(2)
        with colA:
            full_name = st.text_input("Student Full Name *")
            gender = st.selectbox("Gender *", ["Male", "Female"])
            dob = st.date_input("Date of Birth *", min_value=datetime.date(2010,1,1), max_value=datetime.date(2023,12,31))
            class_group = st.selectbox("Class Group *", ["Playgroup","PP1 & PP2","Grade 1 to 6","Grade 7 to 9"])
        with colB:
            term = st.selectbox("Term *", ["Term 1","Term 2","Term 3"])
            parent_name = st.text_input("Parent / Guardian Name *")
            parent_phone = st.text_input("Parent Phone * (07... )")
            amount_now = st.number_input("Amount Being Paid Now (KES) *", min_value=0, value=0)

        total_fee = 0
        try:
            with engine.connect() as conn:
                total_fee = conn.execute(text("SELECT amount FROM fee_structure WHERE class_group=:c AND term=:t"), {"c":class_group,"t":term}).scalar() or 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Fee", f"KES {total_fee}")
            c2.metric("50% Required", f"KES {int(total_fee*0.5)}")
            c3.metric("Balance After", f"KES {total_fee - amount_now}")
            if total_fee > 0 and amount_now > 0:
                bal_after = total_fee - amount_now
                if bal_after == 0:
                    st.success("✅ Full payment! Balance = 0")
                else:
                    st.warning(f"⚠️ Balance remaining: KES {bal_after}")
        except Exception as e:
            st.write(f"Fee not set: {e}")

        if st.button("✅ Admit Student", type="primary", use_container_width=True):
            if not full_name or not parent_name or not parent_phone:
                st.error("Please fill all * fields")
            elif total_fee == 0:
                st.error("Fee structure not set for this Class & Term. Ask Accountant to set it first.")
            elif amount_now < (total_fee * 0.5):
                st.error(f"❌ 50% Rule: Must pay at least KES {int(total_fee*0.5)}")
            else:
                try:
                    with engine.connect() as conn:
                        conn.execute(text("""
                            INSERT INTO students (admission_no, full_name, gender, dob, class_group, term, parent_name, parent_phone, total_fee, paid_amount, balance, status)
                            VALUES (:adm, :name, :gender, :dob, :cg, :term, :pname, :phone, :tf, :paid, :bal, 'active')
                        """), {
                            "adm": auto_adm_no, "name": full_name, "gender": gender, "dob": dob,
                            "cg": class_group, "term": term, "pname": parent_name, "phone": parent_phone,
                            "tf": total_fee, "paid": amount_now, "bal": total_fee - amount_now
                        })
                        conn.execute(text("""
                            INSERT INTO payments (student_id, amount, phone, status)
                            VALUES (:s, :a, :p, 'confirmed')
                        """), {"s": auto_adm_no, "a": amount_now, "p": parent_phone})
                        conn.commit()
                    log_action(user, "STUDENT_ADMITTED", auto_adm_no, f"{full_name}")
                    st.success(f"✅ Admitted! {full_name} - {auto_adm_no} - Balance KES {total_fee-amount_now}")
                    st.balloons()
                except Exception as e:
                    st.error(f"Failed: {e}")

        st.divider()
        st.subheader("📋 All Students - BALANCE Column (Red = Has Not Paid Full)")
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text("SELECT admission_no as ADM, full_name as Student, gender as Gender, dob as DOB, class_group as Class, parent_name as Parent_Name, parent_phone as Phone, total_fee as Total, paid_amount as Paid, balance as BALANCE FROM students ORDER BY id DESC"), conn)
            if not df.empty:
                def highlight_balance(val):
                    return 'background-color: #ffcccc; color: black; font-weight: bold' if val > 0 else 'background-color: #ccffcc; color: black'
                st.dataframe(df.style.applymap(highlight_balance, subset=['BALANCE']), use_container_width=True)
                debtors = df[df['BALANCE'] > 0]
                if not debtors.empty:
                    st.warning(f"⚠️ {len(debtors)} students NOT cleared - Total KES {debtors['BALANCE'].sum()} outstanding")
                    csv = debtors.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Debtors (Parent + Balance)", csv, "debtors_jlc.csv", "text/csv")
                else:
                    st.success("All cleared! ✅")
            else:
                st.info("No students yet - Admit first student above")
        except Exception as e:
            st.error(f"Load error: {e}")

    with tab2:
        st.subheader("Record Extra Payment")
        adm_no = st.text_input("Admission No")
        extra = st.number_input("Amount", min_value=0)
        if st.button("Record Payment"):
            try:
                with engine.connect() as conn:
                    conn.execute(text("UPDATE students SET paid_amount = paid_amount + :a, balance = total_fee - (paid_amount + :a) WHERE admission_no=:adm"), {"a":extra, "adm":adm_no})
                    conn.execute(text("INSERT INTO payments (student_id, amount, status) VALUES (:s, :a, 'confirmed')"), {"s":adm_no, "a":extra})
                    conn.commit()
                st.success("Payment recorded!")
            except Exception as e:
                st.error(f"{e}")

# ---------------- TEACHER ----------------
elif role == "teacher":
    st.header("Teacher - CBC Academics")
    st.write("Teacher module working - Add marks here")
    # Add your CBC subjects code here (same as before)

# ---------------- ACCOUNTANT ----------------
elif role == "accountant":
    st.header("Accountant - Fee Structure & Bills")
    st.write("Set fee structure")
    with st.form("fee_form"):
        cg = st.selectbox("Class", ["Playgroup","PP1 & PP2","Grade 1 to 6","Grade 7 to 9"])
        term = st.selectbox("Term", ["Term 1","Term 2","Term 3"])
        amount = st.number_input("Amount", min_value=0)
        if st.form_submit_button("Set Fee"):
            with engine.connect() as conn:
                conn.execute(text("INSERT INTO fee_structure (class_group, term, amount) VALUES (:c,:t,:a) ON CONFLICT (class_group, term) DO UPDATE SET amount=:a"), {"c":cg,"t":term,"a":amount})
                conn.commit()
            st.success("Fee set!")

# ---------------- ADMIN ----------------
elif role == "admin":
    st.header("Admin Dashboard")
    st.write("Welcome Admin")

else:
    st.write(f"Role {role} dashboard coming soon")
