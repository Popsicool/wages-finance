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


'''

{"current_page":1,"data":[{"sender_id":"Check","status":"unblock","company":"Check Retail","usecase":"One time password for both change and reset of pin and password","country":"Nigeria","created_at":"2023-08-10 14:58:54"},{"sender_id":"CheckRetail","status":"pending","company":"End-Point technology.","usecase":"Hello Akinyemi, Welcome onboard.","country":"Nigeria","created_at":"2023-07-25 11:14:37"},{"sender_id":"N-Alert","status":"unblock","company":null,"usecase":null,"country":null,"created_at":"2019-07-20 13:13:04"}],"first_page_url":"http:\/\/api.ng.termii.com\/api\/sender-id?page=1","from":1,"last_page":1,"last_page_url":"http:\/\/api.ng.termii.com\/api\/sender-id?page=1","next_page_url":null,"path":"http:\/\/api.ng.termii.com\/api\/sender-id","per_page":15,"prev_page_url":null,"to":3,"total":3}
'''