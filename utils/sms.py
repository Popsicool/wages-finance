import requests
from decouple import config

API_KEY = config('TERMII_API_KEY')
TERMII_BASE_URL = config('TERMII_BASE_URL')

class SendSMS:
    @staticmethod
    def sendVerificationCode(info):
        url = TERMII_BASE_URL
        payload = {
                "to": info["number"],
                "from": "N-Alert",
                "sms": f"Your Wages Finance verification code is {info['token']}. Valid for 10 minutes, one-time use only.",
                "type": "plain",
                "channel": "dnd",
                "api_key": API_KEY,
            }
        headers = {
        'Content-Type': 'application/json',
        }
        response = requests.request("POST", url, headers=headers, json=payload)
