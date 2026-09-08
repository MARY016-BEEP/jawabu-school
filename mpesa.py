import os
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")

CONSUMER_SECRET = os.getenv(
    "MPESA_CONSUMER_SECRET"
)

SHORTCODE = os.getenv(
    "MPESA_SHORTCODE"
)

PASSKEY = os.getenv(
    "MPESA_PASSKEY"
)

CALLBACK_URL = os.getenv(
    "MPESA_CALLBACK_URL"
)


# ===================================
# GET ACCESS TOKEN
# ===================================

def get_access_token():

    url = (
        "https://sandbox.safaricom.co.ke/"
        "oauth/v1/generate?grant_type=client_credentials"
    )

    response = requests.get(

        url,

        auth=(
            CONSUMER_KEY,
            CONSUMER_SECRET
        )

    )

    response.raise_for_status()

    return response.json()["access_token"]


# ===================================
# GENERATE PASSWORD
# ===================================

def generate_password():

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    data_to_encode = (
        SHORTCODE
        + PASSKEY
        + timestamp
    )

    encoded = base64.b64encode(
        data_to_encode.encode()
    )

    password = encoded.decode()

    return password, timestamp


# ===================================
# SEND STK PUSH
# ===================================

def stk_push(

    phone_number,

    amount,

    registration_number

):

    access_token = get_access_token()

    password, timestamp = generate_password()

    url = (
        "https://sandbox.safaricom.co.ke/"
        "mpesa/stkpush/v1/processrequest"
    )

    headers = {

        "Authorization":
        f"Bearer {access_token}",

        "Content-Type":
        "application/json"

    }


    payload = {

        "BusinessShortCode":
        SHORTCODE,

        "Password":
        password,

        "Timestamp":
        timestamp,

        "TransactionType":
        "CustomerPayBillOnline",

        "Amount":
        int(amount),

        "PartyA":
        phone_number,

        "PartyB":
        SHORTCODE,

        "PhoneNumber":
        phone_number,

        "CallBackURL":
        CALLBACK_URL,

        "AccountReference":
        registration_number,

        "TransactionDesc":
        "School Fees Payment"

    }


    response = requests.post(

        url,

        json=payload,

        headers=headers

    )


    response.raise_for_status()

    return response.json()