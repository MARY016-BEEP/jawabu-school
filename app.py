import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime, date
import plotly.express as px

# ==========================================
# CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="JAWABU LEARNING CENTRE",
    page_icon="🎓",
    layout="wide"
)

DATABASE = "jawabu_school.db"

# ==========================================
# CUSTOM BABY PINK DESIGN
# ==========================================

st.markdown("""
<style>

.stApp {
    background-color: #FFF5F7;
}

[data-testid="stSidebar"] {
    background-color: #F8C8DC;
}

h1, h2, h3 {
    color: #8B3A62;
}

div[data-testid="metric-container"] {
    background-color: #FFFFFF;
    border: 2px solid #F4B6C2;
    padding: 15px;
    border-radius: 15px;
}

.stButton > button {
    background-color: #E88DAA;
    color: white;
    border-radius: 10px;
    border: none;
    padding: 8px 20px;
}

.stButton > button:hover {
    background-color: #C96C8A;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_connection():
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    return conn


conn = get_connection()
cursor = conn.cursor()


# ==========================================
# CREATE DATABASE TABLES
# ==========================================

def create_tables():

    # USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # STUDENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registration_number TEXT UNIQUE,
        student_name TEXT,
        parent_name TEXT,
        parent_phone TEXT,
        admission_date TEXT,
        gender TEXT,
        dob TEXT,
        nemis_number TEXT,
        class_name TEXT
    )
    """)

    # PAYMENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registration_number TEXT,
        payment_date TEXT,
        amount REAL,
        tuition REAL,
        transport REAL,
        library REAL,
        mpesa_code TEXT,
        payment_method TEXT
    )
    """)

    # BILLS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registration_number TEXT,
        term TEXT,
        academic_year INTEGER,
        tuition_fee REAL,
        transport_fee REAL,
        library_fee REAL,
        arrears REAL,
        total_bill REAL
    )
    """)

    # EXPENSES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_date TEXT,
        category TEXT,
        description TEXT,
        amount REAL
    )
    """)

    # RESULTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registration_number TEXT,
        subject TEXT,
        score REAL,
        term TEXT,
        academic_year INTEGER
    )
    """)

    conn.commit()


create_tables()


# ==========================================
# DEFAULT USERS
# ==========================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_default_users():

    users = [
        ("director", hash_password("director123"), "DIRECTOR"),
        ("accountant", hash_password("account123"), "ACCOUNTANT"),
        ("teacher", hash_password("teacher123"), "TEACHER")
    ]

    for username, password, role in users:
        try:
            cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
            """, (username, password, role))

        except sqlite3.IntegrityError:
            pass

    conn.commit()


create_default_users()


# ==========================================
# FEE STRUCTURE
# ==========================================

FEE_STRUCTURE = {

    "Play Group": 5000,

    "PP1": 7000,

    "PP2": 7000,

    "Grade 1": 10000,

    "Grade 2": 10000,

    "Grade 3": 10000,

    "Grade 4": 10000,

    "Grade 5": 10000,

    "Grade 6": 10000,

    "Grade 7": 12000,

    "Grade 8": 12000,

    "Grade 9": 12000

}


# ==========================================
# AUTO GENERATE REGISTRATION NUMBER
# ==========================================

def generate_registration_number():

    current_year = datetime.now().year

    cursor.execute("SELECT COUNT(*) FROM students")

    count = cursor.fetchone()[0] + 1

    reg_number = f"JLC/{current_year}/{count:04d}"

    return reg_number


# ==========================================
# LOGIN SYSTEM
# ==========================================

def login():

    st.title("🎓 JAWABU LEARNING CENTRE")

    st.subheader("School Administration System")

    username = st.text_input("Username")

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Login"):

        hashed_password = hash_password(password)

        cursor.execute("""
        SELECT role FROM users
        WHERE username=? AND password=?
        """, (username, hashed_password))

        user = cursor.fetchone()

        if user:

            st.session_state.logged_in = True

            st.session_state.username = username

            st.session_state.role = user[0]

            st.success("Login successful!")

            st.rerun()

        else:

            st.error("Invalid username or password")


# ==========================================
# LOGOUT
# ==========================================

def logout():

    st.sidebar.markdown("---")

    if st.sidebar.button("Logout"):

        st.session_state.logged_in = False

        st.session_state.username = None

        st.session_state.role = None

        st.rerun()


# ==========================================
# DIRECTOR DASHBOARD
# ==========================================

def director_dashboard():

    st.title("👩‍💼 DIRECTOR DASHBOARD")

    # TOTAL COLLECTION

    cursor.execute("""
    SELECT COALESCE(SUM(amount),0)
    FROM payments
    """)

    total_collected = cursor.fetchone()[0]


    # TOTAL EXPENSES

    cursor.execute("""
    SELECT COALESCE(SUM(amount),0)
    FROM expenses
    """)

    total_expenses = cursor.fetchone()[0]


    profit = total_collected - total_expenses


    # STUDENTS

    cursor.execute("""
    SELECT COUNT(*)
    FROM students
    """)

    total_students = cursor.fetchone()[0]


    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Students",
        total_students
    )

    col2.metric(
        "Total Fees Collected",
        f"KES {total_collected:,.2f}"
    )

    col3.metric(
        "Total Expenses",
        f"KES {total_expenses:,.2f}"
    )

    col4.metric(
        "Profit / Loss",
        f"KES {profit:,.2f}"
    )


    st.markdown("---")

    st.subheader("Financial Summary")

    finance_data = pd.DataFrame({

        "Category": [
            "Fees Collected",
            "Expenses",
            "Profit/Loss"
        ],

        "Amount": [
            total_collected,
            total_expenses,
            profit
        ]

    })

    fig = px.bar(
        finance_data,
        x="Category",
        y="Amount",
        text="Amount"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ==========================================
# ADMISSION MODULE
# ==========================================

def admission_module():

    st.title("📝 Student Admission")

    registration_number = generate_registration_number()

    st.info(
        f"Auto Generated Registration Number: {registration_number}"
    )

    with st.form("admission_form"):

        student_name = st.text_input(
            "Student Full Name"
        )

        parent_name = st.text_input(
            "Parent / Guardian Name"
        )

        parent_phone = st.text_input(
            "Parent Phone Number (M-Pesa STK)"
        )

        admission_date = st.date_input(
            "Admission Date",
            date.today()
        )

        gender = st.selectbox(
            "Gender",
            ["Male", "Female"]
        )

        dob = st.date_input(
            "Date of Birth"
        )

        nemis_number = st.text_input(
            "NEMIS Number"
        )

        class_name = st.selectbox(
            "Class",
            list(FEE_STRUCTURE.keys())
        )


        submitted = st.form_submit_button(
            "Register Student"
        )


        if submitted:

            if student_name == "" or parent_phone == "":

                st.error(
                    "Student name and parent phone are required"
                )

            else:

                cursor.execute("""
                INSERT INTO students
                (
                    registration_number,
                    student_name,
                    parent_name,
                    parent_phone,
                    admission_date,
                    gender,
                    dob,
                    nemis_number,
                    class_name
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,

                (
                    registration_number,
                    student_name,
                    parent_name,
                    parent_phone,
                    str(admission_date),
                    gender,
                    str(dob),
                    nemis_number,
                    class_name
                ))

                conn.commit()

                st.success(
                    f"Student registered successfully! Registration Number: {registration_number}"
                )


# ==========================================
# FEE BILLING MODULE
# ==========================================

def billing_module():

    st.title("💰 Fee Billing")

    students = pd.read_sql_query(
        "SELECT registration_number, student_name, class_name FROM students",
        conn
    )

    if students.empty:

        st.warning("No students registered")

        return


    student_options = students.apply(
        lambda x: f"{x['registration_number']} - {x['student_name']}",
        axis=1
    ).tolist()


    selected_student = st.selectbox(
        "Select Student",
        student_options
    )


    registration_number = selected_student.split(" - ")[0]


    student = students[
        students["registration_number"] == registration_number
    ].iloc[0]


    base_fee = FEE_STRUCTURE[student["class_name"]]


    term = st.selectbox(
        "Term",
        ["Term 1", "Term 2", "Term 3"]
    )


    academic_year = st.number_input(
        "Academic Year",
        value=datetime.now().year
    )


    transport_fee = st.number_input(
        "Transport Fee",
        min_value=0.0
    )


    library_fee = st.number_input(
        "Library Fee",
        min_value=0.0
    )


    arrears = st.number_input(
        "Balance Carried Forward / Arrears",
        min_value=0.0
    )


    total_bill = (
        base_fee
        + transport_fee
        + library_fee
        + arrears
    )


    st.metric(
        "Total Amount Payable",
        f"KES {total_bill:,.2f}"
    )


    if st.button("Generate Bill"):

        cursor.execute("""
        INSERT INTO bills
        (
            registration_number,
            term,
            academic_year,
            tuition_fee,
            transport_fee,
            library_fee,
            arrears,
            total_bill
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            registration_number,
            term,
            academic_year,
            base_fee,
            transport_fee,
            library_fee,
            arrears,
            total_bill
        ))

        conn.commit()

        st.success("Bill generated successfully")


# ==========================================
# M-PESA PAYMENT MODULE
# ==========================================

def payment_module():

    st.title("📱 M-Pesa & Finance")

    st.subheader("Record Payment")

    students = pd.read_sql_query(
        "SELECT registration_number, student_name FROM students",
        conn
    )

    if students.empty:

        st.warning("No students available")

        return


    selected_student = st.selectbox(

        "Student",

        students.apply(
            lambda x: f"{x['registration_number']} - {x['student_name']}",
            axis=1
        ).tolist()

    )


    registration_number = selected_student.split(" - ")[0]


    amount = st.number_input(
        "Amount Paid",
        min_value=0.0
    )


    payment_method = st.selectbox(

        "Payment Method",

        [
            "M-Pesa",
            "Cash",
            "Bank"
        ]

    )


    mpesa_code = st.text_input(
        "M-Pesa Confirmation Code"
    )


    # PAYMENT SPLITTING

    st.subheader(
        "Payment Allocation"
    )


    tuition = st.number_input(
        "Tuition Amount",
        min_value=0.0
    )


    transport = st.number_input(
        "Transport Amount",
        min_value=0.0
    )


    library = st.number_input(
        "Library Amount",
        min_value=0.0
    )


    total_allocation = (
        tuition
        + transport
        + library
    )


    st.write(
        f"Allocated Amount: KES {total_allocation:,.2f}"
    )


    if total_allocation > amount:

        st.error(
            "Allocation cannot exceed payment amount"
        )


    if st.button("Save Payment"):

        if amount <= 0:

            st.error(
                "Enter a valid amount"
            )

        elif total_allocation > amount:

            st.error(
                "Payment allocation exceeds amount paid"
            )

        else:

            cursor.execute("""
            INSERT INTO payments
            (
                registration_number,
                payment_date,
                amount,
                tuition,
                transport,
                library,
                mpesa_code,
                payment_method
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,

            (
                registration_number,
                str(date.today()),
                amount,
                tuition,
                transport,
                library,
                mpesa_code,
                payment_method
            ))

            conn.commit()

            st.success(
                "Payment successfully recorded"
            )

            st.balloons()


# ==========================================
# FINANCE DASHBOARD
# ==========================================

def finance_dashboard():

    st.title("💵 Finance Dashboard")


    cursor.execute(
        "SELECT COALESCE(SUM(amount),0) FROM payments"
    )

    total = cursor.fetchone()[0]


    cursor.execute(
        "SELECT COALESCE(SUM(tuition),0) FROM payments"
    )

    tuition = cursor.fetchone()[0]


    cursor.execute(
        "SELECT COALESCE(SUM(transport),0) FROM payments"
    )

    transport = cursor.fetchone()[0]


    cursor.execute(
        "SELECT COALESCE(SUM(library),0) FROM payments"
    )

    library = cursor.fetchone()[0]


    col1, col2, col3, col4 = st.columns(4)


    col1.metric(
        "Total Collected",
        f"KES {total:,.2f}"
    )


    col2.metric(
        "Tuition",
        f"KES {tuition:,.2f}"
    )


    col3.metric(
        "Transport",
        f"KES {transport:,.2f}"
    )


    col4.metric(
        "Library",
        f"KES {library:,.2f}"
    )


    st.subheader("Recent Payments")


    payments = pd.read_sql_query("""
    SELECT
        p.registration_number,
        s.student_name,
        p.payment_date,
        p.amount,
        p.payment_method,
        p.mpesa_code
    FROM payments p

    LEFT JOIN students s

    ON p.registration_number = s.registration_number

    ORDER BY p.id DESC
    """, conn)


    st.dataframe(
        payments,
        use_container_width=True
    )


# ==========================================
# EXPENSE MODULE
# ==========================================

def expense_module():

    st.title("📉 Expenses Management")

    categories = [

        "Salary",

        "Food",

        "Books",

        "Electricity",

        "WiFi",

        "Transport",

        "Maintenance",

        "Other"

    ]


    with st.form("expense_form"):

        expense_date = st.date_input(
            "Expense Date",
            date.today()
        )


        category = st.selectbox(
            "Expense Category",
            categories
        )


        description = st.text_area(
            "Description"
        )


        amount = st.number_input(
            "Amount",
            min_value=0.0
        )


        submitted = st.form_submit_button(
            "Record Expense"
        )


        if submitted:

            cursor.execute("""
            INSERT INTO expenses
            (
                expense_date,
                category,
                description,
                amount
            )

            VALUES (?, ?, ?, ?)
            """,

            (
                str(expense_date),
                category,
                description,
                amount
            ))

            conn.commit()

            st.success(
                "Expense recorded successfully"
            )


    st.subheader("Expense Records")


    expenses = pd.read_sql_query(
        "SELECT * FROM expenses ORDER BY id DESC",
        conn
    )


    st.dataframe(
        expenses,
        use_container_width=True
    )


# ==========================================
# FEE DEFAULTERS
# ==========================================

def fee_defaulters():

    st.title("⚠️ Fee Defaulters")

    query = """

    SELECT

        s.registration_number,

        s.student_name,

        s.parent_name,

        s.parent_phone,

        s.class_name,

        COALESCE(
            SUM(b.total_bill),
            0
        ) AS total_billed,

        COALESCE(
            SUM(p.amount),
            0
        ) AS total_paid,

        COALESCE(
            SUM(b.total_bill),
            0
        )

        -

        COALESCE(
            SUM(p.amount),
            0
        )

        AS balance

    FROM students s

    LEFT JOIN bills b

    ON s.registration_number =
    b.registration_number

    LEFT JOIN payments p

    ON s.registration_number =
    p.registration_number

    GROUP BY
        s.registration_number

    HAVING balance > 0

    ORDER BY balance DESC

    """


    data = pd.read_sql_query(
        query,
        conn
    )


    st.dataframe(
        data,
        use_container_width=True
    )


    if not data.empty:

        st.download_button(

            "Download Defaulters List",

            data.to_csv(
                index=False
            ),

            "fee_defaulters.csv",

            "text/csv"

        )


# ==========================================
# CLASS LIST
# ==========================================

def class_list():

    st.title("📚 Class Lists")

    selected_class = st.selectbox(

        "Select Class",

        list(FEE_STRUCTURE.keys())

    )


    students = pd.read_sql_query(

        f"""
        SELECT

            registration_number,

            student_name,

            parent_name,

            parent_phone,

            gender,

            nemis_number

        FROM students

        WHERE class_name = '{selected_class}'

        """,

        conn

    )


    st.dataframe(

        students,

        use_container_width=True

    )


# ==========================================
# M-PESA RECONCILIATION
# ==========================================

def mpesa_reconciliation():

    st.title("🔄 M-Pesa Reconciliation Report")


    mpesa = pd.read_sql_query("""

    SELECT

        p.payment_date,

        p.registration_number,

        s.student_name,

        p.amount,

        p.tuition,

        p.transport,

        p.library,

        p.mpesa_code

    FROM payments p

    LEFT JOIN students s

    ON p.registration_number =
    s.registration_number

    WHERE p.payment_method = 'M-Pesa'

    ORDER BY p.payment_date DESC

    """, conn)


    st.dataframe(

        mpesa,

        use_container_width=True

    )


    if not mpesa.empty:

        total_mpesa = mpesa["amount"].sum()

        st.metric(

            "Total M-Pesa Collections",

            f"KES {total_mpesa:,.2f}"

        )


        st.download_button(

            "Download M-Pesa Reconciliation Report",

            mpesa.to_csv(index=False),

            "mpesa_reconciliation.csv",

            "text/csv"

        )


# ==========================================
# TEACHER ACADEMIC PORTAL
# ==========================================

def teacher_dashboard():

    st.title("👩‍🏫 Teacher Academic Portal")

    st.info(
        "Teachers can manage student academic records only."
    )


    menu = st.selectbox(

        "Academic Menu",

        [
            "Enter Results",
            "View Results",
            "Class List"
        ]

    )


    if menu == "Enter Results":

        students = pd.read_sql_query(
            "SELECT registration_number, student_name FROM students",
            conn
        )


        if not students.empty:

            selected = st.selectbox(

                "Student",

                students.apply(

                    lambda x:
                    f"{x['registration_number']} - {x['student_name']}",

                    axis=1

                ).tolist()

            )


            reg = selected.split(" - ")[0]


            subject = st.text_input(
                "Subject"
            )


            score = st.number_input(

                "Score",

                min_value=0.0,

                max_value=100.0

            )


            term = st.selectbox(
                "Term",
                ["Term 1", "Term 2", "Term 3"]
            )


            if st.button("Save Result"):

                cursor.execute("""

                INSERT INTO results

                (
                    registration_number,
                    subject,
                    score,
                    term,
                    academic_year
                )

                VALUES (?, ?, ?, ?, ?)

                """,

                (
                    reg,
                    subject,
                    score,
                    term,
                    datetime.now().year
                ))

                conn.commit()

                st.success(
                    "Academic result saved"
                )


    elif menu == "View Results":

        results = pd.read_sql_query("""

        SELECT

            s.student_name,

            s.registration_number,

            r.subject,

            r.score,

            r.term,

            r.academic_year

        FROM results r

        LEFT JOIN students s

        ON r.registration_number =
        s.registration_number

        """, conn)


        st.dataframe(
            results,
            use_container_width=True
        )


    elif menu == "Class List":

        class_list()


# ==========================================
# MAIN NAVIGATION
# ==========================================

def main_app():

    role = st.session_state.role

    st.sidebar.title(
        "🎓 JAWABU LEARNING CENTRE"
    )

    st.sidebar.write(
        f"Logged in as: **{role}**"
    )


    # DIRECTOR ACCESS

    if role == "DIRECTOR":

        menu = st.sidebar.radio(

            "Navigation",

            [

                "Director Dashboard",

                "Student Admission",

                "Fee Billing",

                "Finance Dashboard",

                "Expenses",

                "Fee Defaulters",

                "Class Lists",

                "M-Pesa Reconciliation",

                "Teacher Portal"

            ]

        )


        if menu == "Director Dashboard":

            director_dashboard()


        elif menu == "Student Admission":

            admission_module()


        elif menu == "Fee Billing":

            billing_module()


        elif menu == "Finance Dashboard":

            finance_dashboard()


        elif menu == "Expenses":

            expense_module()


        elif menu == "Fee Defaulters":

            fee_defaulters()


        elif menu == "Class Lists":

            class_list()


        elif menu == "M-Pesa Reconciliation":

            mpesa_reconciliation()


        elif menu == "Teacher Portal":

            teacher_dashboard()


    # ACCOUNTANT ACCESS

    elif role == "ACCOUNTANT":

        menu = st.sidebar.radio(

            "Finance Navigation",

            [

                "Finance Dashboard",

                "Fee Billing",

                "Record Payment",

                "Fee Defaulters",

                "M-Pesa Reconciliation"

            ]

        )


        if menu == "Finance Dashboard":

            finance_dashboard()


        elif menu == "Fee Billing":

            billing_module()


        elif menu == "Record Payment":

            payment_module()


        elif menu == "Fee Defaulters":

            fee_defaulters()


        elif menu == "M-Pesa Reconciliation":

            mpesa_reconciliation()


    # TEACHER ACCESS

    elif role == "TEACHER":

        teacher_dashboard()


    logout()


# ==========================================
# APPLICATION START
# ==========================================

if "logged_in" not in st.session_state:

    st.session_state.logged_in = False


if not st.session_state.logged_in:

    login()

else:

    main_app()