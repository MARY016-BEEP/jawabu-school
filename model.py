from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Boolean,
    ForeignKey
)

from sqlalchemy.sql import func

from database import Base


# ============================
# USERS
# ============================

class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    username = Column(
        String,
        unique=True,
        nullable=False
    )

    password_hash = Column(
        String,
        nullable=False
    )

    role = Column(
        String,
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# ============================
# STUDENTS
# ============================

class Student(Base):

    __tablename__ = "students"

    id = Column(Integer, primary_key=True)

    registration_number = Column(
        String,
        unique=True,
        nullable=False
    )

    student_name = Column(String)

    parent_name = Column(String)

    parent_phone = Column(String)

    admission_date = Column(Date)

    gender = Column(String)

    dob = Column(Date)

    nemis_number = Column(String)

    class_name = Column(String)


# ============================
# BILLS
# ============================

class Bill(Base):

    __tablename__ = "bills"

    id = Column(
        Integer,
        primary_key=True
    )

    registration_number = Column(
        String,
        ForeignKey("students.registration_number")
    )

    term = Column(String)

    academic_year = Column(Integer)

    tuition_fee = Column(Float, default=0)

    transport_fee = Column(Float, default=0)

    library_fee = Column(Float, default=0)

    arrears = Column(Float, default=0)

    total_bill = Column(Float)


# ============================
# PAYMENTS
# ============================

class Payment(Base):

    __tablename__ = "payments"

    id = Column(
        Integer,
        primary_key=True
    )

    registration_number = Column(String)

    amount = Column(Float)

    tuition_amount = Column(
        Float,
        default=0
    )

    transport_amount = Column(
        Float,
        default=0
    )

    library_amount = Column(
        Float,
        default=0
    )

    mpesa_receipt = Column(
        String,
        unique=True
    )

    checkout_request_id = Column(
        String,
        unique=True
    )

    payment_date = Column(
        DateTime,
        server_default=func.now()
    )

    status = Column(
        String,
        default="PENDING"
    )


# ============================
# EXPENSES
# ============================

class Expense(Base):

    __tablename__ = "expenses"

    id = Column(
        Integer,
        primary_key=True
    )

    expense_date = Column(Date)

    category = Column(String)

    description = Column(String)

    amount = Column(Float)

    entered_by = Column(String)

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# ============================
# AUDIT LOGS
# ============================

class AuditLog(Base):

    __tablename__ = "audit_logs"

    id = Column(
        Integer,
        primary_key=True
    )

    username = Column(String)

    action = Column(String)

    table_name = Column(String)

    record_id = Column(String)

    old_value = Column(String)

    new_value = Column(String)

    created_at = Column(
        DateTime,
        server_default=func.now()
    )
