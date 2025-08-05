import os
import json
import re
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OUTPUT_DIR = "data"
ADS_FILE = os.path.join(OUTPUT_DIR, "ads.json")
LINKED_FILE = os.path.join(OUTPUT_DIR, "linked_ads.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Local metadata lookup table (extend manually as needed) ---
BOOK_METADATA = {
    "B09BW7F5PZ": {  # Dragon's Kin
        "book_title": "Dragon's Kin",
        "asin": "B09BW7F5PZ",
        "blurb": "Young Kindan has no expectations other than a hard life in the coal mines of Camp Natalon...",
        "cover_url": "https://m.media-amazon.com/images/I/81bApXw2o7L.jpg"
    },
    "B07GZHLJPT": {  # The Jupiter Game
        "book_title": "The Jupiter Game",
        "asin": "B07GZHLJPT",
        "blurb": "Earth enters the Galactic Union. First contact with aliens occurs just after humanity’s first fusion-powered ship reaches Jupiter...",
        "cover_url": "https://m.media-amazon.com/images/I/41mVzJ2Hy1L.jpg"
    },
    "FREEBIE_TITLE": {  # Newsletter freebie example
        "book_title": "Free Starter Book",
        "asin": None,
        "blurb": "A free introduction to the world of...",
        "cover_url": "https://example.com/freebie-cover.jpg"
    }
}

# --- Helpers ---
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def extract_asin(url):
    """Extract ASIN from Amazon URL."""
    if not url:
        return None
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    if match:
        return match.group(1)
    match = re.search(r"/gp/product/([A-Z0-9]{10})", url)
    if match:
        return match.group(1)
    return None

def fetch_metadata_from_openlibrary(asin):
    """Fetch book metadata from Open Library via ISBN lookup."""
    url = f"https://openlibrary.org/isbn/{asin}.json"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            title = data.get("title")
            blurb = data.get("description", "")
            if isinstance(blurb, dict):
                blurb = blurb.get("value", "")
            cover_url = None
            if "covers" in data:
                cover_url = f"https://covers.openlibrary.org/b/id/{data['covers'][0]}-L.jpg"
            return {
                "book_title": title or f"Unknown ({asin})",
                "asin": asin,
                "blurb": blurb,
                "cover_url": cover_url
            }
    except Exception as e:
        print(f"⚠️ Could not fetch metadata for {asin}: {e}")
    return {
        "book_title": f"Unknown ({asin})",
        "asin": asin,
        "blurb": None,
        "cover_url": None
    }

def classify_url(url):
    """Classify ad type and return metadata."""
    if not url:
        return "unknown", None

    url_lower = url.lower()

    # Lead-gen: BookFunnel / newsletter
    if "bookfunnel.com" in url_lower or "newsletter" in url_lower:
        return "lead_gen", BOOK_METADATA.get("FREEBIE_TITLE")

    # Amazon: Extract ASIN and look up metadata
    if "amazon.com" in url_lower:
        asin = extract_asin(url)
        if asin:
            metadata = BOOK_METADATA.get(asin)
            if not metadata:
                print(f"🔍 Fetching metadata for ASIN {asin}...")
                metadata = fetch_metadata_from_openlibrary(asin)
            return "sale", metadata

    return "unknown", None

# --- Main ---
def main():
    ads_data = load_json(ADS_FILE, [])
    if not ads_data:
        print(f"❌ No {ADS_FILE} found. Run fetch_ads.py first.")
        return

    linked_data = []

    print("🔗 Auto-linking ads to books/newsletter...\n")

    for campaign in ads_data:
        print(f"\n=== Campaign: {campaign['name']} ===")
        for adset in campaign["adsets"]:
            for ad in adset["ads"]:
                ad_id = ad["id"]
                ad_name = ad["name"]
                target_url = ad.get("target_url")

                ad_type, metadata = classify_url(target_url)

                if metadata:
                    print(f"✅ Linked {ad_name} ({ad_type}) → {metadata['book_title']}")
                    linked_data.append({
                        "campaign_name": campaign["name"],
                        "campaign_id": campaign["campaign_id"],
                        "adset_name": adset["name"],
                        "adset_id": adset["adset_id"],
                        "ad_name": ad_name,
                        "ad_id": ad_id,
                        "target_url": target_url,
                        "type": ad_type,
                        **metadata
                    })
                else:
                    print(f"⚠️ Could not auto-link {ad_name} (URL: {target_url})")
                    title = input("Book Title (or leave blank to skip): ").strip()
                    if not title:
                        continue
                    asin = input("ASIN (optional): ").strip()
                    blurb = input("Blurb (optional): ").strip()
                    cover_url = input("Cover URL (optional): ").strip()
                    linked_data.append({
                        "campaign_name": campaign["name"],
                        "campaign_id": campaign["campaign_id"],
                        "adset_name": adset["name"],
                        "adset_id": adset["adset_id"],
                        "ad_name": ad_name,
                        "ad_id": ad_id,
                        "target_url": target_url,
                        "type": ad_type if ad_type != "unknown" else "manual",
                        "book_title": title,
                        "asin": asin or None,
                        "blurb": blurb or None,
                        "cover_url": cover_url or None
                    })

                save_json(LINKED_FILE, linked_data)

    print(f"\n💾 Saved linked ads to {LINKED_FILE}")

if __name__ == "__main__":
    main()