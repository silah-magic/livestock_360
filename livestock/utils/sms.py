# livestock/utils/sms.py
import africastalking
from decouple import config

username = config('AT_USERNAME')
api_key = config('AT_API_KEY')

africastalking.initialize(username, api_key)
sms = africastalking.SMS

def send_sms(recipients, message):
    """
    Send an SMS.
    recipients: list of phone numbers (e.g., ['+2547...'])
    message: string
    """
    try:
        response = sms.send(message, recipients)
        print(f"SMS sent: {response}")
        return response
    except Exception as e:
        print(f"SMS failed: {e}")
        return None