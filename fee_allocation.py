# Automatically allocate payment to balances: Tuition -> Library -> Transport -> Lunch
def auto_allocate(student_id, amount_paid, outstanding_balances):
    """
    outstanding_balances = {"tuition": 20000, "library": 2000, "transport": 3000}
    """
    allocation = {}
    remaining = amount_paid
    priority = ["tuition", "library", "transport", "lunch", "exam"]

    for fee_type in priority:
        if remaining <= 0: break
        owed = outstanding_balances.get(fee_type, 0)
        if owed > 0:
            pay = min(owed, remaining)
            allocation[fee_type] = pay
            remaining -= pay

    if remaining > 0:
        allocation["overpayment"] = remaining

    return allocation
