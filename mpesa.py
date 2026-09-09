import requests, base64, os, datetime
from requests.auth import HTTPBasicAuth
import streamlit as st
from sqlalchemy import text
from database import get_engine

def get_mpesa_token():
    key = os.getenv("MPESA_CONSUMER_KEY") or st.secrets.get("MPESA_CONSUMER_KEY")
    secret = os.getenv("MPESA_CONSUMER_SECRET") or st.secrets.get("MPESA_CONSUMER_SECRET")
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=HTTPBasicAuth(key, secret))
    return r.json()['access_token']

def stk_push(phone, amount, admission_no):
    token = get_mpesa_token()
    
    # Format phone to 254...
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    shortcode = os.getenv("MPESA_SHORTCODE") or st.secrets.get("MPESA_SHORTCODE", "174379")
    passkey = os.getenv("MPESA_PASSKEY") or st.secrets.get("MPESA_PASSKEY")
    
    password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode()
    
    # YOUR CALLBACK URL - You will get this after deploying callback_server
    callback_url = os.getenv("CALLBACK_URL") or st.secrets.get("CALLBACK_URL", "https://your-callback.onrender.com/callback")

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": admission_no,
        "TransactionDesc": f"Fees for {admission_no}"
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    res = requests.post(url, json=payload, headers=headers)
    
    # Save as PENDING - will become confirmed after callback
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO payments (student_id, amount, phone, status)
                VALUES (:s, :a, :p, 'pending')
            """), {"s": admission_no, "a": amount, "p": phone})
            conn.commit()
    except Exception as e:
        print(f"Failed to save pending: {e}")

    return res.json()
