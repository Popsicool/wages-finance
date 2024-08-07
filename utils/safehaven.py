import requests
from decouple import config
from user.models import SafeHavenAPIDetails
from requests.exceptions import ReadTimeout
from datetime import datetime, timedelta
from django.utils import timezone
import uuid


TOKEN = config("SAFEHAVEN_TOKEN")
ACCOUNT = config("SAFEHAVEN_Account")
CLIENT_ID = config("CLIENT_ID")
CLIENT_ASSERTION = config("CLIENT_ASSERTION")
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "ClientID": CLIENT_ID,
    "Authorization": "Bearer abc"
}

def safehaven_auth(a=None):
    global headers
    token = SafeHavenAPIDetails.objects.first()
    current_time = timezone.now()
    token_expired = token and (current_time - token.updated_at) > timedelta(minutes=2)

    if a is not None or not token or token_expired:
        url = "https://api.sandbox.safehavenmfb.com/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_id": CLIENT_ID,
            "client_assertion": CLIENT_ASSERTION
        }
        local_headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        response = requests.post(url, json=payload, headers=local_headers)

        if response.status_code == 201:
            data = response.json()
            acc_token = data['access_token']
            client_id = data.get('client_id', '')  # Use .get() to provide a default value
            ibs_client_id = data.get('ibs_client_id', '')
            ibs_user_id = data.get('ibs_user_id', '')

            if token:
                token.acc_token = acc_token
                token.client_id = client_id
                token.ibs_client_id = ibs_client_id
                token.ibs_user_id = ibs_user_id
                token.updated_at = current_time
                token.save()
            else:
                token = SafeHavenAPIDetails.objects.create(
                    acc_token=acc_token,
                    client_id=client_id,
                    ibs_client_id=ibs_client_id,
                    ibs_user_id=ibs_user_id,
                    updated_at=current_time
                )
                token.save()

            # Update the global headers with the new access token
            headers.update({
                "Authorization": f"Bearer {acc_token}"
            })
    else:
        return

def safe_initiate(data):
    safehaven_auth()  # Ensure the token is up-to-date

    url = "https://api.sandbox.safehavenmfb.com/identity/v2"
    payload = {
        "type": data["type"],
        "number": str(data["number"]),
        "debitAccountNumber": ACCOUNT
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            return (True, response.json()['data'])
        if response.status_code == 403:
            # Token expired, get a new token and retry
            safehaven_auth(a=True)
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                return (True, response.json()['data'])
            if response.status_code == 403:
                return (False, "Expired token - Access Restricted!")
        if response.status_code == 500:
            return (False, "Service not responding, please retry")
        return (False, response.json()['data']['debitMessage'])
    except ReadTimeout:
        return (False, "Verification server not responding")
    except requests.exceptions.RequestException as e:
        return (False, "Verification server not responding, please retry latter")

def safe_validate(data):
    safehaven_auth()  # Ensure the token is up-to-date

    url = "https://api.sandbox.safehavenmfb.com/identity/v2/validate"
    payload = {
        "type": data["type"],
        "identityId": data["_id"],
        "otp": data["otp"]
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 201:
        return (True, response.json()["data"]["providerResponse"])
    if response.status_code == 403:
        # Token expired, get a new token and retry
        safehaven_auth(a=True)
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            return (True, response.json()["data"]["providerResponse"])
        if response.status_code == 403:
            return (False, "Expired token - Access Restricted!")
    return (False, "Error")

def create_safehaven_account(data):
    safehaven_auth()  # Ensure the token is up-to-date

    url = "https://api.sandbox.safehavenmfb.com/accounts/subaccount"
    payload = {
        "phoneNumber": data["phone"],
        "emailAddress": data["email"],
        "identityType": "BVN",
        "externalReference": str(uuid.uuid4()),
        "identityNumber": data["bvn"],
        "identityId": data["_id"],
        "otp": data["otp"]
    }
    response = requests.post(url, json=payload, headers=headers)
    resp = response.json()
    if response.status_code == 403:
        # Token expired, get a new token and retry
        safehaven_auth(a=True)
        response = requests.post(url, json=payload, headers=headers)
        resp = response.json()
        if response.status_code == 201:
            return (resp["data"]["accountNumber"], resp["data"]["accountName"])
        if response.status_code == 403:
            return ("Expired token - Access Restricted!", None)
    return (resp["data"]["accountNumber"], resp["data"]["accountName"])
