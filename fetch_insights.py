import os
import json
import time
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

# Files
OUTPUT_DIR = "data"
ADS_FILE = os.path.join(OUTPUT_DIR, "ads.json")
INSIGHTS_FILE = os.path.join(OUTPUT_DIR, "ad_insights.json")

# Ensure data directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Helper Functions --- #
def fb_get(endpoint, params=None):
    """GET request to Facebook Graph API with simple retry/backoff."""
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


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# --- Main Function --- #
def main():
    ads_data = load_json(ADS_FILE, [])
    insights_output = []

    if not ads_data:
        print(f"❌ No ads.json found in {ADS_FILE}. Run fetch_ads.py first.")
        return

    for campaign in ads_data:
        print(f"\n📣 Campaign: {campaign['name']} ({campaign['campaign_id']})")

        for adset in campaign["adsets"]:
            for ad in adset["ads"]:
                ad_id = ad["id"]
                print(f"   📊 Fetching insights for Ad: {ad['name']} ({ad_id})")

                metrics = fb_get(f"{ad_id}/insights", {
                    "fields": "impressions,clicks,spend,cpc,ctr,actions",
                    "date_preset": "last_30d"
                }).get("data", [])

                if metrics:
                    insights_output.append({
                        "campaign_name": campaign["name"],
                        "campaign_id": campaign["campaign_id"],
                        "adset_name": adset["name"],
                        "adset_id": adset["adset_id"],
                        "ad_name": ad["name"],
                        "ad_id": ad_id,
                        "metrics": metrics[0]  # Insights returns a list
                    })

                time.sleep(1)  # Throttle to avoid hitting limits

    save_json(INSIGHTS_FILE, insights_output)
    print(f"\n✅ Saved insights for {len(insights_output)} ads to {INSIGHTS_FILE}")


if __name__ == "__main__":
    main()