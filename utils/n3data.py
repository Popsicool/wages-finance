import base64
from decouple import config
import requests


USERNAME = config("N3USERNAME")
PASSWORD = config("N3PASSWORD")
BASE_URL = config("N3BASEURL")
TOKEN = config("N3TOKEN")

credentials = f"{USERNAME}:{PASSWORD}"
encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
headers = {
    "Authorization": f"Basic {encoded_credentials}"
}

class DataAPI:
    @staticmethod
    def get_user():
        url = f"{BASE_URL}/user"
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            json_response = response.json()
            return json_response
    @staticmethod
    def buy_data(data):
        networks = {
            "MTN": 1,
            "AIRTEL":2,
            "GLO": 3,
            "9MOBILE":4
        }
        url = f"{BASE_URL}/data"
        plan_id_to_find = data.get("plan_id")
        if not plan_id_to_find:
            return (False, "No plan selected")
        selected_plan = next((plan for plan in DATA_PLANS if plan["plan_id"] == plan_id_to_find), None)
        if not selected_plan:
            return (False, "Invalid plan")
        newtork_id = networks.get(selected_plan["network"])
        payload = {
            "network": newtork_id,
            "phone": data["number"],
            "plan_type": "VTU",
            "bypass": False,
            "data_plan": selected_plan["plan_id"],
            "request-id": data["reference"]
        }
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json"
        }
        # Make POST request
        response = requests.post(url, headers=headers, json=payload)
        # Check if the request was successful
        json_response = response.json()
        if response.status_code == 200:
            # Load JSON response
            status = json_response.get('status')
            if status and status == 'success':
                return (True, "success")
            return (False, json_response.get('message', "Failed"))
        else:
            return (False, json_response.get('message'))
    @staticmethod
    def buy_airtime(data):
        desired_network = data["network"]
        networks = {
            "MTN": 1,
            "AIRTEL":2,
            "GLO": 3,
            "9MOBILE":4
        }
        url = f"{BASE_URL}/topup/"
        newtork_id = networks.get(desired_network)
        if not newtork_id:
            return (False, "Invalid network")
        payload = {
            "network": newtork_id,
            "phone": data["number"],
            "plan_type": "VTU",
            "bypass": False,
            "amount": data["amount"],
            "request-id": data["reference"]
        }
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json"
        }
        # Make POST request
        response = requests.post(url, headers=headers, json=payload)
        # Check if the request was successful
        json_response = response.json()
        if response.status_code == 200:
            # Load JSON response
            status = json_response.get('status')
            if status and status == 'success':
                return (True, "success")
            return (False, json_response.get('message', "Failed"))
        else:
            return (False, json_response.get('message'))

DATA_PLANS =  [
        {
            "plan_name": "500MB",
            "plan_id": "1",
            "amount": "130.00",
            "plan_type": "SME",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "1GB",
            "plan_id": "2",
            "amount": "260.00",
            "plan_type": "SME",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "2GB",
            "plan_id": "3",
            "amount": "520.00",
            "plan_type": "SME",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "3GB",
            "plan_id": "4",
            "amount": "780.00",
            "plan_type": "SME",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "5GB",
            "plan_id": "5",
            "amount": "1,300.00",
            "plan_type": "SME",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "10GB",
            "plan_id": "6",
            "amount": "2,600.00",
            "plan_type": "SME",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "1.5GB",
            "plan_id": "36",
            "amount": "950.00",
            "plan_type": "GIFTING",
            "plan_day": "1 Month",
            "network": "9MOBILE"
        },
        {
            "plan_name": "2GB",
            "plan_id": "37",
            "amount": "1,100.00",
            "plan_type": "GIFTING",
            "plan_day": "1 Month",
            "network": "9MOBILE"
        },
        {
            "plan_name": "3GB",
            "plan_id": "38",
            "amount": "1,400.00",
            "plan_type": "GIFTING",
            "plan_day": "1 Month",
            "network": "9MOBILE"
        },
        {
            "plan_name": "4.5GB",
            "plan_id": "39",
            "amount": "1,800.00",
            "plan_type": "GIFTING",
            "plan_day": "1 Month",
            "network": "9MOBILE"
        },
        {
            "plan_name": "500MB",
            "plan_id": "46",
            "amount": "140.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "AIRTEL"
        },
        {
            "plan_name": "1GB",
            "plan_id": "47",
            "amount": "280.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "AIRTEL"
        },
        {
            "plan_name": "2GB",
            "plan_id": "48",
            "amount": "560.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "AIRTEL"
        },
        {
            "plan_name": "5GB",
            "plan_id": "49",
            "amount": "1,400.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "AIRTEL"
        },
        {
            "plan_name": "500MB",
            "plan_id": "50",
            "amount": "130.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "1GB",
            "plan_id": "51",
            "amount": "260.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "2GB",
            "plan_id": "52",
            "amount": "520.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "3GB",
            "plan_id": "53",
            "amount": "780.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "5GB",
            "plan_id": "54",
            "amount": "1,300.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "10GB",
            "plan_id": "55",
            "amount": "2,600.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "10GB",
            "plan_id": "56",
            "amount": "2,800.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "AIRTEL"
        },
        {
            "plan_name": "200MB",
            "plan_id": "57",
            "amount": "50.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "GLO"
        },
        {
            "plan_name": "500MB",
            "plan_id": "58",
            "amount": "145.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "GLO"
        },
        {
            "plan_name": "1GB",
            "plan_id": "59",
            "amount": "290.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "GLO"
        },
        {
            "plan_name": "2GB",
            "plan_id": "60",
            "amount": "580.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "GLO"
        },
        {
            "plan_name": "3GB",
            "plan_id": "61",
            "amount": "870.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "GLO"
        },
        {
            "plan_name": "5GB",
            "plan_id": "62",
            "amount": "1,450.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "GLO"
        },
        {
            "plan_name": "10GB",
            "plan_id": "63",
            "amount": "2,900.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1 Month",
            "network": "GLO"
        },
        {
            "plan_name": "5GB",
            "plan_id": "65",
            "amount": "1,200.00",
            "plan_type": "GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "3GB",
            "plan_id": "66",
            "amount": "720.00",
            "plan_type": "GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "2GB",
            "plan_id": "67",
            "amount": "480.00",
            "plan_type": "GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "1GB",
            "plan_id": "68",
            "amount": "240.00",
            "plan_type": "GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "500MB",
            "plan_id": "69",
            "amount": "120.00",
            "plan_type": "GIFTING",
            "plan_day": "1 Month",
            "network": "MTN"
        },
        {
            "plan_name": "300MB",
            "plan_id": "70",
            "amount": "90.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1Month",
            "network": "AIRTEL"
        },
        {
            "plan_name": "100MB",
            "plan_id": "71",
            "amount": "40.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1Month",
            "network": "AIRTEL"
        },
        {
            "plan_name": "500MB",
            "plan_id": "72",
            "amount": "100.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1Month",
            "network": "9MOBILE"
        },
        {
            "plan_name": "1GB",
            "plan_id": "73",
            "amount": "200.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1Month",
            "network": "9MOBILE"
        },
        {
            "plan_name": "2GB",
            "plan_id": "74",
            "amount": "400.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1Month",
            "network": "9MOBILE"
        },
        {
            "plan_name": "3GB",
            "plan_id": "75",
            "amount": "600.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1Month",
            "network": "9MOBILE"
        },
        {
            "plan_name": "5GB",
            "plan_id": "76",
            "amount": "1,000.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1Month",
            "network": "9MOBILE"
        },
        {
            "plan_name": "10GB",
            "plan_id": "77",
            "amount": "2,000.00",
            "plan_type": "COOPERATE GIFTING",
            "plan_day": "1Month",
            "network": "9MOBILE"
        },
        {
            "plan_name": "1GB",
            "plan_id": "78",
            "amount": "225.00",
            "plan_type": "GIFTING",
            "plan_day": "1Day Awoof Data",
            "network": "MTN"
        },
        {
            "plan_name": "3.5GB",
            "plan_id": "79",
            "amount": "550.00",
            "plan_type": "GIFTING",
            "plan_day": "2Days Awoof Data",
            "network": "MTN"
        },
        {
            "plan_name": "15GB",
            "plan_id": "80",
            "amount": "2,050.00",
            "plan_type": "GIFTING",
            "plan_day": "7Days Awoof Data",
            "network": "MTN"
        },
        {
            "plan_name": "100MB",
            "plan_id": "82",
            "amount": "70.00",
            "plan_type": "GIFTING",
            "plan_day": "1Day Awoof Data",
            "network": "AIRTEL"
        },
        {
            "plan_name": "300MB",
            "plan_id": "83",
            "amount": "130.00",
            "plan_type": "GIFTING",
            "plan_day": "2Days Awoof Data",
            "network": "AIRTEL"
        },
        {
            "plan_name": "1GB",
            "plan_id": "84",
            "amount": "240.00",
            "plan_type": "GIFTING",
            "plan_day": "2Days Awoof Data",
            "network": "AIRTEL"
        },
        {
            "plan_name": "2GB",
            "plan_id": "85",
            "amount": "370.00",
            "plan_type": "GIFTING",
            "plan_day": "2Days Awoof Data",
            "network": "AIRTEL"
        },
        {
            "plan_name": "3GB",
            "plan_id": "86",
            "amount": "600.00",
            "plan_type": "GIFTING",
            "plan_day": "7Days Awoof Data",
            "network": "AIRTEL"
        },
        {
            "plan_name": "4GB",
            "plan_id": "87",
            "amount": "1,100.00",
            "plan_type": "GIFTING",
            "plan_day": "1Month Awoof Data",
            "network": "AIRTEL"
        },
        {
            "plan_name": "10GB",
            "plan_id": "88",
            "amount": "2,100.00",
            "plan_type": "GIFTING",
            "plan_day": "1Month Awoof Data",
            "network": "AIRTEL"
        },
        {
            "plan_name": "15GB",
            "plan_id": "89",
            "amount": "3,100.00",
            "plan_type": "GIFTING",
            "plan_day": "1Month Awoof Data",
            "network": "AIRTEL"
        },
        {
            "plan_name": "1GB",
            "plan_id": "90",
            "amount": "230.00",
            "plan_type": "GIFTING",
            "plan_day": "1Day Awoof Data",
            "network": "GLO"
        },
        {
            "plan_name": "2GB",
            "plan_id": "91",
            "amount": "350.00",
            "plan_type": "GIFTING",
            "plan_day": "1Day Awoof Data",
            "network": "GLO"
        },
        {
            "plan_name": "3.5GB",
            "plan_id": "92",
            "amount": "550.00",
            "plan_type": "GIFTING",
            "plan_day": "2Days Awoof Data",
            "network": "GLO"
        },
        {
            "plan_name": "15GB",
            "plan_id": "93",
            "amount": "2,300.00",
            "plan_type": "GIFTING",
            "plan_day": "7Days Awoof Data",
            "network": "GLO"
        }
    ]
