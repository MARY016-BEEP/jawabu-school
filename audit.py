from database import SessionLocal
from models import AuditLog


def create_audit_log(

    username,

    action,

    table_name,

    record_id,

    old_value="",

    new_value=""

):

    db = SessionLocal()


    log = AuditLog(

        username=username,

        action=action,

        table_name=table_name,

        record_id=str(record_id),

        old_value=str(old_value),

        new_value=str(new_value)

    )


    db.add(log)

    db.commit()

    db.close()