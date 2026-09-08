from flask import Flask, request, jsonify

from database import SessionLocal

from models import Payment


app = Flask(__name__)


@app.route(
    "/mpesa/callback",
    methods=["POST"]
)

def mpesa_callback():

    data = request.get_json()

    try:

        callback = (
            data["Body"]
            ["stkCallback"]
        )

        result_code = callback[
            "ResultCode"
        ]

        checkout_id = callback[
            "CheckoutRequestID"
        ]


        # SUCCESSFUL PAYMENT

        if result_code == 0:

            metadata = callback[
                "CallbackMetadata"
            ]["Item"]


            mpesa_receipt = None

            amount = None


            for item in metadata:

                if item["Name"] == "MpesaReceiptNumber":

                    mpesa_receipt = item["Value"]


                elif item["Name"] == "Amount":

                    amount = item["Value"]


            db = SessionLocal()


            payment = db.query(Payment).filter(

                Payment.checkout_request_id
                == checkout_id

            ).first()


            if payment:

                payment.status = "SUCCESS"

                payment.mpesa_receipt = (
                    mpesa_receipt
                )

                payment.amount = amount

                db.commit()

                db.close()


        return jsonify({

            "ResultCode": 0,

            "ResultDesc": "Accepted"

        })


    except Exception as e:

        print(e)

        return jsonify({

            "ResultCode": 1,

            "ResultDesc": "Failed"

        })