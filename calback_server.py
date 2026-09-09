from flask import Flask, request, jsonify
from database import get_engine
from fee_allocation import auto_allocate
from notifications import send_sms
from audit import log_action
from sqlalchemy import text

app = Flask(__name__)

@app.route('/callback', methods=['POST'])
def mpesa_callback():
    data = request.json
    try:
        stk = data['Body']['stkCallback']
        if stk['ResultCode'] == 0:
            meta = stk['CallbackMetadata']['Item']
            mpesa_code = next(i['Value'] for i in meta if i['Name'] == 'MpesaReceiptNumber')
            amount = next(i['Value'] for i in meta if i['Name'] == 'Amount')
            phone = next(i['Value'] for i in meta if i['Name'] == 'PhoneNumber')
            account_ref = stk['MerchantRequestID'] # Or use AccountReference you sent

            # TODO: Get student balances from DB
            # For demo: auto allocate
            # allocation = auto_allocate(account_ref, amount, balances)
            
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("INSERT INTO payments (student_id, mpesa_code, amount, phone, status) VALUES (:s, :c, :a, :p, 'confirmed')"),
                             {"s": account_ref, "c": mpesa_code, "a": amount, "p": phone})
                conn.commit()

            send_sms(phone, f"Received KES {amount}. Mpesa Code {mpesa_code} allocated to fees. Thank you - Jawabu Learning Centre.")
            log_action("SYSTEM", "PAYMENT_CONFIRMED", mpesa_code, f"Amount {amount}")

        return jsonify({"ResultCode": 0})
    except Exception as e:
        print(e)
        return jsonify({"ResultCode": 1})

if __name__ == '__main__':
    app.run(port=5000)
