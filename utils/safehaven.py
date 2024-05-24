import requests
from decouple import config


TOKEN = config("SAFEHAVEN_TOKEN")
ACCOUNT = config("SAFEHAVEN_Account")
headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "AUthorization": f"Bearer {TOKEN}"
    }

def safe_initiate(data):
    url = "https://api.sandbox.safehavenmfb.com/identity/v2"

    payload = {
        "type": data["type"],
        "number": data["number"],
        "debitAccountNumber": ACCOUNT
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return (True, "success")
    return (False, "Error")

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