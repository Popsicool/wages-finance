import requests
from decouple import config


TOKEN = config("SAFEHAVEN_TOKEN")
ACCOUNT = config("SAFEHAVEN_Account")
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

def safe_initiate(data):
    url = "https://api.sandbox.safehavenmfb.com/identity/v2"
    payload = {
        "type": data["type"],
        "number": str(data["number"]),
        "debitAccountNumber": ACCOUNT
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return (True, response.json()['data']['_id'])
    if response.status_code == 403:
        print("ops")
        return (False, "Expired token - Access Restricted!")
    if response.status_code == 500:
        return (False, "Service not responding, please retry")
    return (False, response.json()['data']['debitMessage'])

def safe_validate(data):
    url = "https://api.sandbox.safehavenmfb.com/identity/v2/validate"
    payload = {
        "type": data["type"],
        "identityId": data["_id"],
        "otp": data["otp"]
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return (True, "success")
    return (False, "Error")