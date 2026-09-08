import os
def send_sms(phone, message):
    # For real SMS use Africa's Talking
    print(f"SMS to {phone}: {message}")
    # Implement AT API here
    return True

def send_announcement(message):
    # Loop all parent phones from DB and send
    print(f"Announcement: {message}")
    return True
