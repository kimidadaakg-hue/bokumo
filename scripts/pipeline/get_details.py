#!/usr/bin/env python3
"""
Fetch Place Details from Google Places API (New) for each shop in discovered.json.

Reads:  scripts/pipeline/discovered.json
Writes: scripts/pipeline/details.json
Resume: scripts/pipeline/details_progress.json
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DISCOVERED_PATH = os.path.join(SCRIPT_DIR, "discovered.json")
DETAILS_PATH = os.path.join(SCRIPT_DIR, "details.json")
PROGRESS_PATH = os.path.join(SCRIPT_DIR, "details_progress.json")

API_BASE = "https://places.googleapis.com/v1/places"
FIELD_MASK = "id,displayName,formattedAddress,location,primaryType,websiteUri,photos,googleMapsUri,businessStatus,reviews"
SLEEP_INTERVAL = 0.2
SAVE_EVERY = 100


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def fetch_place_details(place_id, api_key):
    """Fetch details for a single place. Returns (data_dict, error_string)."""
    url = f"{API_BASE}/{place_id}?languageCode=ja&regionCode=JP"
    req = urllib.request.Request(url)
    req.add_header("X-Goog-Api-Key", api_key)
    req.add_header("X-Goog-FieldMask", FIELD_MASK)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body), None
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return None, f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return None, str(e)


def extract_record(raw):
    """Convert raw API response to output record."""
    display_name = raw.get("displayName", {})
    name = display_name.get("text", "") if isinstance(display_name, dict) else str(display_name)

    location = raw.get("location", {})
    lat = location.get("latitude", 0.0)
    lng = location.get("longitude", 0.0)

    website_uri = raw.get("websiteUri", "")
    photo_reference = ""
    photos = raw.get("photos", [])
    if photos and isinstance(photos, list) and len(photos) > 0:
        photo_reference = photos[0].get("name", "")

    # reviews を整形
    reviews_raw = raw.get("reviews", []) or []
    reviews_formatted = []
    for r in reviews_raw[:5]:
        text = ""
        ot = r.get("originalText") or r.get("text") or {}
        if isinstance(ot, dict):
            text = ot.get("text", "")
        rating = r.get("rating", 0)
        if text:
            reviews_formatted.append({"rating": rating, "text": text})

    record = {
        "place_id": raw.get("id", ""),
        "name": name,
        "address": raw.get("formattedAddress", ""),
        "lat": lat,
        "lng": lng,
        "primaryType": raw.get("primaryType", ""),
        "websiteUri": website_uri,
        "photo_reference": photo_reference,
        "googleMapsUri": raw.get("googleMapsUri", ""),
        "reviews": reviews_formatted,
    }

    if website_uri and "instagram.com" in website_uri:
        record["instagram_url"] = website_uri

    return record


def main():
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        print("ERROR: GOOGLE_PLACES_API_KEY environment variable is not set.")
        sys.exit(1)

    # Load discovered shops
    discovered = load_json(DISCOVERED_PATH)
    if not discovered:
        print(f"ERROR: {DISCOVERED_PATH} not found or empty.")
        sys.exit(1)

    # Load progress (set of already-processed place_ids)
    progress_list = load_json(PROGRESS_PATH, [])
    processed_ids = set(progress_list)

    # Load existing details
    details = load_json(DETAILS_PATH, [])
    # Index existing details by place_id for dedup
    existing_ids = {r["place_id"] for r in details}

    total = len(discovered)
    count_operational = 0
    count_closed = 0
    count_errors = 0
    count_skipped = len(processed_ids)
    unsaved = 0

    print(f"Total shops in discovered.json: {total}")
    print(f"Already processed (resuming): {count_skipped}")
    print()

    for i, shop in enumerate(discovered):
        place_id = shop.get("place_id", "")
        shop_name = shop.get("name", place_id)

        if place_id in processed_ids:
            continue

        raw, err = fetch_place_details(place_id, api_key)

        if err:
            print(f"  [{i+1}/{total}] {shop_name} -> ERROR: {err}")
            count_errors += 1
            # Still mark as processed to avoid infinite retry on permanent errors
            processed_ids.add(place_id)
            unsaved += 1
            time.sleep(SLEEP_INTERVAL)
            continue

        business_status = raw.get("businessStatus", "")

        if business_status and business_status != "OPERATIONAL":
            print(f"  [{i+1}/{total}] {shop_name} -> SKIPPED ({business_status})")
            count_closed += 1
            processed_ids.add(place_id)
            unsaved += 1
            time.sleep(SLEEP_INTERVAL)
            if unsaved >= SAVE_EVERY:
                save_json(PROGRESS_PATH, list(processed_ids))
                save_json(DETAILS_PATH, details)
                unsaved = 0
            continue

        record = extract_record(raw)

        if record["place_id"] not in existing_ids:
            details.append(record)
            existing_ids.add(record["place_id"])

        processed_ids.add(place_id)
        count_operational += 1
        unsaved += 1

        print(f"  [{i+1}/{total}] {shop_name} -> OK")

        time.sleep(SLEEP_INTERVAL)

        # Save progress periodically
        if unsaved >= SAVE_EVERY:
            save_json(PROGRESS_PATH, list(processed_ids))
            save_json(DETAILS_PATH, details)
            print(f"  ... progress saved ({len(details)} shops in details.json)")
            unsaved = 0

    # Final save
    save_json(PROGRESS_PATH, list(processed_ids))
    save_json(DETAILS_PATH, details)

    # Summary
    print()
    print("=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"  Total in discovered.json : {total}")
    print(f"  Previously processed     : {count_skipped}")
    print(f"  Operational (saved)      : {count_operational}")
    print(f"  Closed/non-operational   : {count_closed}")
    print(f"  Errors                   : {count_errors}")
    print(f"  Total in details.json    : {len(details)}")
    print()


if __name__ == "__main__":
    main()
