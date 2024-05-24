import requests
from decouple import config

API_KEY = config('TERMII_API_KEY')

class SendSMS:
    @staticmethod
    def sendVerificationCode(info):
        url = "https://api.ng.termii.com/api/sms/send"
        payload = {
                "to": info["number"],
                "from": "Check",
                "sms": f"Your verification toke is {info['token']}",
                "type": "plain",
                "channel": "generic",
                "api_key": API_KEY, 
            }
        headers = {
        'Content-Type': 'application/json',
        }
        response = requests.request("POST", url, headers=headers, json=payload)
        print(response.text)
