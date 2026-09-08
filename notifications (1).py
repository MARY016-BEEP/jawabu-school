import os

from twilio.rest import Client

from dotenv import load_dotenv


load_dotenv()


def send_sms(phone, message):

    account_sid = os.getenv(
        "SMS_ACCOUNT_SID"
    )

    auth_token = os.getenv(
        "SMS_AUTH_TOKEN"
    )

    sms_number = os.getenv(
        "SMS_PHONE_NUMBER"
    )


    client = Client(

        account_sid,

        auth_token

    )


    message = client.messages.create(

        body=message,

        from_=sms_number,

        to=phone

    )


    return message.sid