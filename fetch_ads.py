import os
import json
import time
import requests
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("FB_AD_ACCOUNT_ID")
API_VERSION = "v23.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
AD_ACCOUNT = f"act_{AD_ACCOUNT_ID}"

# Files
OUTPUT_DIR = "data"
ADS_FILE = os.path.join(OUTPUT_DIR, "ads.json")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "fetch_progress.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def fb_get(endpoint, params=None):
    """GET request to Facebook Graph API with extended backoff."""
    if params is None:
        params = {}
    params["access_token"] = ACCESS_TOKEN
    url = f"{BASE_URL}/{endpoint}"

    max_attempts = 10
    wait_time = 5  # start at 5s

    for attempt in range(max_attempts):
        response = requests.get(url, params=params)

        # Debug API usage
        usage = {
            "app_usage": response.headers.get("X-App-Usage"),
            "account_usage": response.headers.get("X-Ad-Account-Usage")
        }
        if any(usage.values()):
            print(f"📊 API Usage: {usage}")

        if response.status_code == 200:
            return response.json()

        if "User request limit reached" in response.text:
            print(f"⚠️ Rate limit hit. Waiting {wait_time}s before retry {attempt+1}/{max_attempts}...")
            time.sleep(wait_time)
            wait_time = min(wait_time * 2, 300)  # cap at 5 minutes
            continue

        print(f"❌ API error {response.status_code} on {url}")
        try:
            print(response.json())
        except Exception:
            print(response.text)
        return {}

    raise Exception("❌ Too many failed retries — aborting after extended backoff.")


def normalize_amazon_url(url):
    """Strip tracking parameters from Amazon URLs."""
    if not url:
        return url
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def fetch_campaigns():
    """Fetch only ACTIVE campaigns."""
    print("📣 Fetching ACTIVE campaigns...")
    campaigns = fb_get(f"{AD_ACCOUNT}/campaigns", {
        "fields": "id,name,status,effective_status",
        "limit": 100
    }).get("data", [])

    active_campaigns = [c for c in campaigns if c.get("status") == "ACTIVE"]
    print(f"✅ Found {len(active_campaigns)} active campaigns out of {len(campaigns)} total")
    return active_campaigns


def fetch_adsets(campaign_id):
    """Fetch only ACTIVE ad sets."""
    adsets = fb_get(f"{campaign_id}/adsets", {
        "fields": "id,name,status",
        "limit": 100
    }).get("data", [])
    return [a for a in adsets if a.get("status") == "ACTIVE"]


def fetch_creative_details(creative_id):
    """Fetch full creative data for a given creative ID."""
    fields = (
        "object_story_spec{"
        "link_data{"
        "link,"
        "child_attachments{link},"
        "call_to_action{value{link}}"
        "}"
        "},"
        "object_url,"
        "image_url,"
        "instagram_permalink_url,"
        "name"
    )
    return fb_get(f"{creative_id}", {"fields": fields})


def extract_target_url(creative_data):
    """Extract the destination URL from a creative."""
    target_url = None
    url_source = "none"

    oss = creative_data.get("object_story_spec", {})
    link_data = oss.get("link_data", {})

    if "link" in link_data:
        target_url = link_data["link"]
        url_source = "link_data.link"
    elif "child_attachments" in link_data:
        for child in link_data["child_attachments"]:
            if "link" in child:
                target_url = child["link"]
                url_source = "child_attachments.link"
                break
    elif "call_to_action" in link_data and "value" in link_data["call_to_action"]:
        target_url = link_data["call_to_action"]["value"].get("link")
        url_source = "call_to_action.value.link"
    elif creative_data.get("object_url"):
        target_url = creative_data["object_url"]
        url_source = "creative.object_url"

    return target_url, url_source


def fetch_ads(adset_id):
    """Fetch only ACTIVE ads and pull full creative details separately."""
    ads = fb_get(f"{adset_id}/ads", {
        "fields": "id,name,status,creative{id}",
        "limit": 100
    }).get("data", [])

    active_ads = []
    for ad in ads:
        if ad.get("status") != "ACTIVE":
            continue

        creative_id = ad.get("creative", {}).get("id")
        target_url, url_source = None, "no_creative"

        if creative_id:
            creative_data = fetch_creative_details(creative_id)
            ad["creative"] = creative_data  # ✅ store full creative object in ad
            target_url, url_source = extract_target_url(creative_data)

        print(f"DEBUG: Ad '{ad.get('name')}' URL source: {url_source}, raw: {target_url}")

        if target_url:
            target_url = normalize_amazon_url(target_url)

        print(f"DEBUG: Ad '{ad.get('name')}' normalized target_url: {target_url}")

        ad["target_url"] = target_url
        ad["url_source"] = url_source
        active_ads.append(ad)

    return active_ads


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
    start = not last_id

    for campaign in campaigns:
        if not start:
            if campaign["id"] == last_id:
                start = True
            else:
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
            time.sleep(1)
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

    print("🎉 All active campaigns processed!")


if __name__ == "__main__":
    main()