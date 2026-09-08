def send_fee_reminders():

    students = get_students_with_balances()

    for student in students:

        message = f"""
JAWABU LEARNING CENTRE

Dear {student.parent_name},

Your child's current school fee balance is:

KES {student.balance:,.2f}

Please make payment at your earliest convenience.

Thank you.