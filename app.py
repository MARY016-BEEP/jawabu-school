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


# ---------------- TEACHER - CBC  ----------------
# ---------------- TEACHER - CBC WITH SUBJECT TABS + TOTAL/MEAN/GRADE ----------------
elif role == "teacher":
    st.header("👩‍🏫 Teacher - CBC Assessment - JAWABU LEARNING CENTER")
    st.caption("CBC Curriculum: Tabs per Subject | Total Marks | Mean Score | CBC Grading (EE/ME/AE/BE)")

    # CBC Subjects - OFFICIAL
    CBC_SUBJECTS = {
        "Playgroup": ["Language", "Mathematics", "Environmental", "Psychomotor", "Religious"],
        "PP1 & PP2": ["Language", "Mathematics", "Environmental", "Psychomotor", "Religious", "Creative Arts"],
        "Grade 1 to 6": ["Mathematics", "English", "Kiswahili", "Science & Tech", "SST", "CRE", "Creative Arts", "Agriculture"],
        "Grade 7 to 9": ["Mathematics", "English", "Kiswahili", "Integrated Science", "Social Studies", "CRE", "Pre-Tech", "Agriculture", "Creative Arts"]
    }

    def get_cbc_grade(score):
        if score >= 80: return "EE1" # Exceeding Expectation
        if score >= 65: return "EE2"
        if score >= 50: return "ME1" # Meeting Expectation
        if score >= 35: return "ME2"
        if score >= 20: return "AE" # Approaching
        return "BE" # Below

    def get_mean_grade(mean):
        if mean >= 75: return "EE - Exceeding"
        if mean >= 50: return "ME - Meeting"
        if mean >= 25: return "AE - Approaching"
        return "BE - Below"

    c1, c2, c3 = st.columns(3)
    with c1:
        sel_class = st.selectbox("Class Group", list(CBC_SUBJECTS.keys()), key="cbc_class")
    with c2:
        sel_term = st.selectbox("Term", ["Term 1","Term 2","Term 3"], key="cbc_term")
    with c3:
        sel_year = st.selectbox("Year", [2025,2026], index=1)

    subjects = CBC_SUBJECTS[sel_class]
    st.info(f"**{sel_class} - {sel_term} {sel_year}** | {len(subjects)} Subjects | Grading: 80+ = EE, 50+ = ME, 20+ = AE")

    # Ensure tables exist
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cbc_grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_no TEXT, student_name TEXT, class_group TEXT,
                term TEXT, year TEXT, subject TEXT, score INTEGER, grade TEXT
            )
        """))
        conn.commit()

    # Load students
    with engine.connect() as conn:
        students_df = pd.read_sql(text("SELECT admission_no, full_name FROM students WHERE class_group=:c AND term=:t ORDER BY full_name"), conn, params={"c": sel_class, "t": sel_term})

    if students_df.empty:
        st.error(f"❌ No students in {sel_class} - {sel_term}. Login as Reception → Admit students first in {sel_class}.")
        st.stop()

    st.success(f"✅ {len(students_df)} students loaded")

    # Create TABS for each subject + Summary tab
    tab_labels = subjects + ["📊 TOTAL / MEAN / GRADE"]
    tabs = st.tabs(tab_labels)

    # --- SUBJECT TABS ---
    for idx, subject in enumerate(subjects):
        with tabs[idx]:
            st.subheader(f"{subject} - Enter Marks (0-100)")

            # Load existing marks for this subject
            with engine.connect() as conn:
                existing = pd.read_sql(text("SELECT admission_no, score FROM cbc_grades WHERE class_group=:c AND term=:t AND year=:y AND subject=:s"),
                                       conn, params={"c": sel_class, "t": sel_term, "y": str(sel_year), "s": subject})

            # Build editable table
            entry_df = students_df.copy()
            entry_df["Score (0-100)"] = 0
            entry_df["Grade"] = "BE"

            if not existing.empty:
                score_map = dict(zip(existing["admission_no"], existing["score"]))
                entry_df["Score (0-100)"] = entry_df["admission_no"].map(score_map).fillna(0).astype(int)

            entry_df["Grade"] = entry_df["Score (0-100)"].apply(get_cbc_grade)

            edited = st.data_editor(
                entry_df[["admission_no","full_name","Score (0-100)","Grade"]],
                use_container_width=True,
                disabled=["admission_no","full_name","Grade"],
                key=f"editor_{subject}"
            )

            if st.button(f"💾 Save {subject} Marks", key=f"save_{subject}", type="primary", use_container_width=True):
                with engine.connect() as conn:
                    # Delete old for this subject
                    conn.execute(text("DELETE FROM cbc_grades WHERE class_group=:c AND term=:t AND year=:y AND subject=:s"),
                                 {"c": sel_class, "t": sel_term, "y": str(sel_year), "s": subject})
                    for _, row in edited.iterrows():
                        sc = int(row["Score (0-100)"])
                        gr = get_cbc_grade(sc)
                        conn.execute(text("""
                            INSERT INTO cbc_grades (admission_no, student_name, class_group, term, year, subject, score, grade)
                            VALUES (:adm, :name, :cg, :term, :year, :sub, :sc, :gr)
                        """), {"adm": row["admission_no"], "name": row["full_name"], "cg": sel_class, "term": sel_term, "year": str(sel_year), "sub": subject, "sc": sc, "gr": gr})
                    conn.commit()
                st.success(f"✅ {subject} marks saved!")
                st.rerun()

    # --- TOTAL / MEAN / GRADE TAB ---
    with tabs[-1]:
        st.subheader("📊 Overall - Total, Mean & CBC Grading")
        try:
            with engine.connect() as conn:
                all_marks = pd.read_sql(text("SELECT admission_no, student_name, subject, score FROM cbc_grades WHERE class_group=:c AND term=:t AND year=:y"),
                                        conn, params={"c": sel_class, "t": sel_term, "y": str(sel_year)})

            if all_marks.empty:
                st.info("No marks entered yet. Enter marks in subject tabs first.")
            else:
                # Pivot to get total and mean
                pivot = all_marks.pivot_table(index=["admission_no","student_name"], columns="subject", values="score", aggfunc="max").fillna(0)
                pivot["TOTAL"] = pivot.sum(axis=1)
                pivot["MEAN"] = (pivot["TOTAL"] / len(subjects)).round(1)
                pivot["GRADE"] = pivot["MEAN"].apply(get_mean_grade)
                pivot["RANK"] = pivot["MEAN"].rank(ascending=False, method="min").astype(int)
                pivot = pivot.sort_values("RANK")

                # Color mean
                def color_grade(val):
                    if "EE" in str(val): return 'background-color: #c6efce; color: #006100; font-weight: bold'
                    if "ME" in str(val): return 'background-color: #ffeb9c; color: #9c6500; font-weight: bold'
                    if "AE" in str(val): return 'background-color: #ffcc99; color: #7a4a00'
                    return 'background-color: #ffc7ce; color: #9c0006; font-weight: bold'

                st.dataframe(pivot.style.applymap(color_grade, subset=["GRADE"]), use_container_width=True, height=500)

                c1, c2 = st.columns(2)
                c1.metric("Class Mean", f"{pivot['MEAN'].mean():.1f}%")
                c1.metric("Top Student", f"{pivot.iloc[0]['MEAN']:.1f}% - {pivot.index[0][1]}")

                csv = pivot.reset_index().to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Full CBC Report (Total/Mean/Grade)", csv, f"{sel_class}_{sel_term}_CBC_Report.csv", "text/csv", type="primary", use_container_width=True)
        except Exception as e:
            st.error(f"Error loading totals: {e}")
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
