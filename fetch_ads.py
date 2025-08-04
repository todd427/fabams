import os
import json
import time
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("FB_AD_ACCOUNT_ID")
API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
AD_ACCOUNT = f"act_{AD_ACCOUNT_ID}"

# Files
OUTPUT_DIR = "data"
ADS_FILE = os.path.join(OUTPUT_DIR, "ads.json")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "fetch_progress.json")

# Ensure data/ directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fb_get(endpoint, params=None):
    """GET request to Facebook Graph API with backoff handling."""
    if params is None:
        params = {}
    params["access_token"] = ACCESS_TOKEN
    url = f"{BASE_URL}/{endpoint}"

    for attempt in range(5):
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        elif "User request limit reached" in response.text:
            wait_time = 2 ** attempt
            print(f"⚠️ Rate limit hit. Backing off for {wait_time}s...")
            time.sleep(wait_time)
        else:
            print(f"❌ API error: {response.status_code}")
            try:
                print(response.json())
            except Exception:
                print(response.text)
            return {}

    raise Exception("❌ Too many failed retries — aborting.")


def fetch_campaigns():
    print("📣 Fetching campaigns...")
    return fb_get(f"{AD_ACCOUNT}/campaigns", {
        "fields": "id,name,status,effective_status",
        "limit": 100
    }).get("data", [])


def fetch_adsets(campaign_id):
    return fb_get(f"{campaign_id}/adsets", {
        "fields": "id,name,status",
        "limit": 100
    }).get("data", [])


def fetch_ads(adset_id):
    return fb_get(f"{adset_id}/ads", {
        "fields": "id,name,status,creative",
        "limit": 100
    }).get("data", [])


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def log_start(campaign):
    print()
    print(f"[{datetime.now().isoformat()}] 🚀 START: {campaign['name']} ({campaign['id']})")


def log_finish(campaign):
    print(f"[{datetime.now().isoformat()}] ✅ FINISHED: {campaign['name']} ({campaign['id']})")
    print("-" * 50)


def main():
    output = load_json(ADS_FILE, [])
    progress = load_json(PROGRESS_FILE, {"last_campaign_id": None})
    last_id = progress.get("last_campaign_id")

    campaigns = fetch_campaigns()
    start = not last_id  # If no progress file, start immediately

    for campaign in campaigns:
        if not start:
            if campaign["id"] == last_id:
                start = True
            continue

        log_start(campaign)

        campaign_obj = {
            "campaign_id": campaign["id"],
            "name": campaign["name"],
            "status": campaign["status"],
            "adsets": []
        }

        adsets = fetch_adsets(campaign["id"])
        for adset in adsets:
            time.sleep(1)  # throttle
            ads = fetch_ads(adset["id"])
            adset_obj = {
                "adset_id": adset["id"],
                "name": adset["name"],
                "status": adset["status"],
                "ads": ads
            }
            campaign_obj["adsets"].append(adset_obj)

        output.append(campaign_obj)
        save_json(ADS_FILE, output)
        save_json(PROGRESS_FILE, {"last_campaign_id": campaign["id"]})

        log_finish(campaign)

    print("🎉 All campaigns processed!")


if __name__ == "__main__":
    main()