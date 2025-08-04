import os
import requests
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
FB_AD_ACCOUNT_ID = os.getenv("FB_AD_ACCOUNT_ID")

# Sanity check
if not FB_ACCESS_TOKEN or not FB_AD_ACCOUNT_ID:
    print("⚠️ Missing FB_ACCESS_TOKEN or FB_AD_ACCOUNT_ID in .env")
    exit(1)

# Prefix "act_" to the account ID
ad_account_api_path = f"act_{FB_AD_ACCOUNT_ID}"

# Facebook API endpoint
url = f"https://graph.facebook.com/v19.0/{ad_account_api_path}/campaigns"
params = {
    "access_token": FB_ACCESS_TOKEN,
    "fields": "id,name,status,effective_status",
    "limit": 25
}

# Make the request
response = requests.get(url, params=params)

# Handle response
if response.status_code == 200:
    data = response.json()
    print("✅ Campaigns:")
    for campaign in data.get("data", []):
        print(f"📣 {campaign['name']} (ID: {campaign['id']}, Status: {campaign['status']})")
else:
    print("❌ Error fetching campaigns:")
    print(response.status_code)
    print(response.text)