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


def get_all_ad_fields(sample_ad_id):
    """Fetch the full list of available fields for the ad object."""
    meta = fb_get(f"{sample_ad_id}", {"metadata": 1})
    fields = meta.get("metadata", {}).get("fields", [])
    field_names = [f["name"] for f in fields]
    return field_names


def dump_full_ad(ad_id, field_list):
    """Dump all ad fields for a single ad."""
    fields_param = ",".join(field_list)
    ad_data = fb_get(ad_id, {"fields": fields_param})
    out_path = os.path.join(OUTPUT_DIR, f"ad_{ad_id}_full.json")
    with open(out_path, "w") as f:
        json.dump(ad_data, f, indent=2)
    print(f"✅ Full ad dump saved to {out_path}")


def main():
    print("📥 Fetching a sample ad ID...")
    ads = fb_get(f"{AD_ACCOUNT}/ads", {"limit": 1}).get("data", [])
    if not ads:
        print("❌ No ads found.")
        return

    sample_ad_id = ads[0]["id"]
    print(f"Using sample ad ID: {sample_ad_id}")

    print("🔍 Getting all available fields...")
    all_fields = get_all_ad_fields(sample_ad_id)
    print(f"Found {len(all_fields)} fields.")

    print("📥 Dumping full ad data...")
    dump_full_ad(sample_ad_id, all_fields)


if __name__ == "__main__":
    main()