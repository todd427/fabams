import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("FB_AD_ACCOUNT_ID")
API_VERSION = "v23.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
AD_ACCOUNT = f"act_{AD_ACCOUNT_ID}"

# Output folder
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fb_get(endpoint, params=None):
    if params is None:
        params = {}
    params["access_token"] = ACCESS_TOKEN
    url = f"{BASE_URL}/{endpoint}"
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()


def enumerate_ads():
    """Fetch all ads and dump raw JSON for inspection."""
    print("📥 Fetching ads (no filtering)...")

    ads = fb_get(f"{AD_ACCOUNT}/ads", {
        "fields": ",".join(["id", "name", "creative", "status", "ad_review_feedback"]),
        "limit": 10  # adjust if you want more
    }).get("data", [])

    output_path = os.path.join(OUTPUT_DIR, "ads_raw.json")
    with open(output_path, "w") as f:
        json.dump(ads, f, indent=2)

    print(f"✅ Saved raw ad dump to {output_path}")
    print("💡 Open this file and search for 'http' or 'link' to find URL fields.")

    return ads


if __name__ == "__main__":
    ads = enumerate_ads()
    print(f"🔍 Found {len(ads)} ads in raw dump.")