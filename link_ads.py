import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# File paths
OUTPUT_DIR = "data"
ADS_FILE = os.path.join(OUTPUT_DIR, "ads.json")
LINKED_FILE = os.path.join(OUTPUT_DIR, "linked_ads.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    ads_data = load_json(ADS_FILE, [])
    if not ads_data:
        print(f"❌ No {ADS_FILE} found. Run fetch_ads.py first.")
        return

    linked_data = []

    print("📚 Linking ads to books...")
    print("Press Enter to keep an existing value (if editing). Type 'skip' to skip an ad.\n")

    for campaign in ads_data:
        print(f"\n=== Campaign: {campaign['name']} ===")
        for adset in campaign["adsets"]:
            for ad in adset["ads"]:
                # Check if already linked
                existing_entry = next((x for x in linked_data if x["ad_id"] == ad["id"]), None)
                if existing_entry:
                    print(f"↪ Already linked: {ad['name']}")
                    continue

                print(f"\n🆔 Ad ID: {ad['id']}")
                print(f"📣 Ad Name: {ad['name']}")

                # User input for mapping
                title = input("Book Title: ").strip()
                if title.lower() == "skip":
                    continue

                asin = input("ASIN (optional): ").strip()
                blurb = input("Blurb (optional): ").strip()
                cover_url = input("Cover Image URL (optional): ").strip()

                linked_data.append({
                    "campaign_name": campaign["name"],
                    "campaign_id": campaign["campaign_id"],
                    "adset_name": adset["name"],
                    "adset_id": adset["adset_id"],
                    "ad_name": ad["name"],
                    "ad_id": ad["id"],
                    "book_title": title,
                    "asin": asin,
                    "blurb": blurb,
                    "cover_url": cover_url
                })

                save_json(LINKED_FILE, linked_data)
                print(f"✅ Linked {ad['name']} → {title}")

    print(f"\n💾 Saved linked ads to {LINKED_FILE}")


if __name__ == "__main__":
    main()