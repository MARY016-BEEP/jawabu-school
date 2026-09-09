from fastapi import FastAPI, Request
from sqlalchemy import text
from database import get_engine
import os

app = FastAPI()
engine = get_engine()

@app.post("/callback")
async def mpesa_callback(request: Request):
    data = await request.json()
    print("Mpesa Callback Received:", data)

    try:
        # Daraja sends this structure
        stk_callback = data.get('Body', {}).get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')
        metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])

        # Get amount, phone, receipt
        amount = 0
        phone = ""
        receipt = ""
        for item in metadata:
            if item.get('Name') == 'Amount':
                amount = item.get('Value')
            if item.get('Name') == 'PhoneNumber':
                phone = str(item.get('Value'))
            if item.get('Name') == 'MpesaReceiptNumber':
                receipt = item.get('Value')

        # If payment succeeded (ResultCode 0)
        if result_code == 0 and amount:
            with engine.connect() as conn:
                # 1. Find the pending payment by phone and amount (latest)
                pending = conn.execute(text("""
                    SELECT id, student_id FROM payments 
                    WHERE phone=:p AND amount=:a AND status='pending'
                    ORDER BY created_at DESC LIMIT 1
                """), {"p": phone, "a": amount}).mappings().first()

                if pending:
                    # Update payment to confirmed
                    conn.execute(text("""
                        UPDATE payments SET status='confirmed', student_id=:r 
                        WHERE id=:id
                    """), {"r": receipt, "id": pending['id']})
                    
                    # Update student balance
                    admission_no = pending['student_id']
                    conn.execute(text("""
                        UPDATE students 
                        SET paid_amount = paid_amount + :amt,
                            balance = total_fee - (paid_amount + :amt)
                        WHERE admission_no=:adm
                    """), {"amt": amount, "adm": admission_no})
                    
                    conn.commit()
                    print(f"✅ Payment confirmed: {admission_no} paid {amount}")

        return {"ResultCode": 0, "ResultDesc": "Accepted"}
    except Exception as e:
        print(f"Callback error: {e}")
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

@app.get("/")
def home():
    return {"status": "Jawabu Learning Center Callback Server is Running!"}
