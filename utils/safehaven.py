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
BASE_URL = config("SAFE_HAVEN_BASE_URL")
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
    token_expired = token and (
        current_time - token.updated_at) > timedelta(minutes=2)

    if a is not None or not token or token_expired:
        url = f"{BASE_URL}/oauth2/token"
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
            # Use .get() to provide a default value
            client_id = data.get('client_id', '')
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

    url = f"{BASE_URL}/identity/v2"
    payload = {
        "type": data["type"],
        "number": str(data["number"]),
        "debitAccountNumber": ACCOUNT
    }
    try:
        response = requests.post(url, json=payload, headers=headers)

        resp = response.json()
        if response.status_code == 201:
            if "data" in resp.keys():
                return (True, response.json()['data'])
            if resp['statusCode'] == 403:
                safehaven_auth(a=True)
                response = requests.post(url, json=payload, headers=headers)
                resp = response.json()
                if response.status_code == 201:
                    if "data" in resp.keys():
                        return (True, response.json()['data'])
                    if resp['statusCode'] == 403:
                        return (False, "An error occured from the bank, Please retry latter")
        if response.status_code == 403:
            # Token expired, get a new token and retry
            safehaven_auth(a=True)
            response = requests.post(url, json=payload, headers=headers)
            resp = response.json()
            if response.status_code == 201:
                if "data" in resp.keys():
                    return (True, response.json()['data'])
                return (False, "An error occured from the bank, Please retry latter")
        if response.status_code == 500:
            return (False, "Service not responding, please retry")
        return (False, response.json()['data']['debitMessage'])
    except ReadTimeout:
        return (False, "Verification server not responding")
    except requests.exceptions.RequestException as e:
        return (False, "Verification server not responding, please retry latter")


def safe_validate(data):
    safehaven_auth()  # Ensure the token is up-to-date
    url = f"{BASE_URL}/identity/v2/validate"
    payload = {
        "type": data["type"],
        "identityId": data["_id"],
        "otp": data["otp"]
    }
    response = requests.post(url, json=payload, headers=headers)
    resp = response.json()

    if response.status_code == 201:
        if "data" in resp.keys():
            return (True, response.json()["data"]["providerResponse"])
        if resp['statusCode'] == 400:
            if resp["message"] == 'OTP already verified.':
                return (True, "VERIFIED")
        if resp['statusCode'] == 403:
            safehaven_auth(a=True)
            response = requests.post(url, json=payload, headers=headers)
            resp = response.json()
            if "data" in resp.keys():
                return (True, response.json()["data"]["providerResponse"])
            return (False, "An error occured from the bank, Please retry latter")
        return (False, resp["message"])
    if response.status_code == 403:
        # Token expired, get a new token and retry
        safehaven_auth(a=True)
        response = requests.post(url, json=payload, headers=headers)
        resp = response.json()
        if response.status_code == 201:
            if "data" in resp.keys():
                return (True, resp["data"]["providerResponse"])
        return (False, "An error occured from the bank, Please retry latter")
    return (False, "An error occured from the bank, Please retry latter")


def create_safehaven_account(data):
    safehaven_auth()  # Ensure the token is up-to-date
    url = f"{BASE_URL}/accounts/subaccount"
    payload = {
        "phoneNumber": data["phone"],
        "emailAddress": data["email"],
        "identityType": "vID",
        "externalReference": str(uuid.uuid4()),
        # "identityNumber": data["bvn"],
        "identityId": data["_id"],
        # "otp": data["otp"],
        "autoSweep": True,
        "autoSweepDetails":{
            "schedule": "Instant",
            "accountNumber": ACCOUNT
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    resp = response.json()
    if response.status_code == 201:
        if "data" in resp.keys():
            return (resp["data"]["accountNumber"], resp["data"]["accountName"])
        if resp['statusCode'] == 403:
            safehaven_auth(a=True)
            response = requests.post(url, json=payload, headers=headers)
            resp = response.json()
            if "data" in resp.keys():
                return (True, response.json()["data"]["providerResponse"])
            return (False, "An error occured from the bank, Please retry latter")
        return (False, resp["message"])
    if response.status_code == 403:
        # Token expired, get a new token and retry
        safehaven_auth(a=True)
        response = requests.post(url, json=payload, headers=headers)
        resp = response.json()
        if response.status_code == 201:
            if "data" in resp.keys():
                return (resp["data"]["accountNumber"], resp["data"]["accountName"])
            return (False, "An error occured from the bank, Please retry latter")
    if not "data" in resp:
        return (False, resp["message"])
    return (resp["data"]["accountNumber"], resp["data"]["accountName"])


def safe_name_enquires(data):
    safehaven_auth()  # Ensure the token is up-to-date
    url = f"{BASE_URL}/transfers/name-enquiry"
    payload = {
        "bankCode": data["bankCode"],
        "accountNumber": data["accountNumber"],
    }
    response = requests.post(url, json=payload, headers=headers)
    resp = response.json()
    if response.status_code == 201:
        if "data" in resp.keys():
            reply = {"id": resp["data"]["sessionId"],
                     "accountName": resp["data"]["accountName"]}
            return (True, reply)
        if resp['statusCode'] == 403:
            safehaven_auth(a=True)
            response = requests.post(url, json=payload, headers=headers)
            resp = response.json()
            if "data" in resp.keys():
                return (True, resp["data"]["sessionId"])
            return (False, "An error occured from the bank, Please retry latter")
    if response.status_code == 403:
        safehaven_auth(a=True)
        response = requests.post(url, json=payload, headers=headers)
        resp = response.json()
        if response.status_code == 201:
            if "data" in resp.keys():
                reply = {"id": resp["data"]["sessionId"],
                         "accountName": resp["data"]["accountName"]}
                return (True, reply)
            return (False, "An error occured from the bank, Please retry latter")
    return (False, resp["message"])


def send_money(data):
    safehaven_auth()  # Ensure the token is up-to-date
    url = f"{BASE_URL}/transfers"
    payload = {
        "nameEnquiryReference": data["nameEnquiryReference"],
        "debitAccountNumber": ACCOUNT,
        "beneficiaryBankCode": data["beneficiaryBankCode"],
        "beneficiaryAccountNumber": data["beneficiaryAccountNumber"],
        "amount": float(data["amount"]),
        "saveBeneficiary": True,
        "narration": data["narration"],
        "paymentReference": data["paymentReference"]
    }
    response = requests.post(url, json=payload, headers=headers)
    resp = response.json()
    if response.status_code == 201:
        if resp['message'] == 'Approved or completed successfully':
            return (True, {"message": "success"})
        if resp['statusCode'] == 403:
            safehaven_auth(a=True)
            response = requests.post(url, json=payload, headers=headers)
            resp = response.json()
            if response.status_code == 201:
                if resp['message'] == 'Approved or completed successfully':
                    return (True, {"message": "success"})
            return (False, "An error occured from the bank, Please retry latter")
    if response.status_code == 403:
        safehaven_auth(a=True)
        response = requests.post(url, json=payload, headers=headers)
        resp = response.json()
        if response.status_code == 201:
            if resp['message'] == 'Approved or completed successfully':
                return (True, {"message": "success"})
            return (False, "An error occured from the bank, Please retry latter")
    return (False, resp["message"])


{'nameEnquiryReference': '090286240910173734650948860449', 'debitAccountNumber': '0116805935', 'beneficiaryBankCode': '000013', 'beneficiaryAccountNumber': '0115382115',
    'amount': 200.0, 'saveBeneficiary': True, 'narration': 'Withdrawal of 200 from wages finance wallet balance', 'paymentReference': 'dc977dcd-7694-48cc-b060-dd7a6a49cce3'}
{'statusCode': 200, 'responseCode': '00', 'message': 'Approved or completed successfully', 'data': {'queued': False, '_id': '66e0854cbb96b0002419c3e1', 'client': '66a80d22adefa3002485ea9d', 'account': '66a80d23adefa3002485eaec', 'type': 'Outwards', 'sessionId': '090286240910174340861360869647', 'nameEnquiryReference': '090286240910173734650948860449', 'paymentReference': 'dc977dcd-7694-48cc-b060-dd7a6a49cce3', 'mandateReference': None, 'isReversed': False, 'reversalReference': None, 'provider': 'NIBSS', 'providerChannel': 'NIP', 'providerChannelCode': '2', 'destinationInstitutionCode': '000013', 'creditAccountName': 'AKINOLA SAMSON OLUWASEGUN',
                                                                                                    'creditAccountNumber': '0115382115', 'creditBankVerificationNumber': None, 'creditKYCLevel': '2', 'debitAccountName': 'WAGES TECHNOLOGY LIMITED', 'debitAccountNumber': '0116805935', 'debitBankVerificationNumber': None, 'debitKYCLevel': '3', 'transactionLocation': '9.0932,7.4429', 'narration': 'Withdrawal of 200 from wages finance wallet balance', 'amount': 200, 'fees': 10, 'vat': 0, 'stampDuty': 0, 'responseCode': None, 'responseMessage': None, 'status': 'Created', 'isDeleted': False, 'createdAt': '2024-09-10T17:43:40.850Z', 'createdBy': '66d1c233c767c70024e4cc28', 'updatedAt': '2024-09-10T17:43:40.850Z', '__v': 0}}
