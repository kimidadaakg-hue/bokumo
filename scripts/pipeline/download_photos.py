#!/usr/bin/env python3
"""
Download Google Place Photos for kid-friendly shops.

Reads:  scripts/pipeline/kid_friendly.json
Writes: public/photos/{place_id}.jpg (image files)
        scripts/pipeline/kid_friendly.json (updated with image_url)
Resume: scripts/pipeline/photo_progress.json
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
KID_FRIENDLY_PATH = os.path.join(SCRIPT_DIR, "kid_friendly.json")
PROGRESS_PATH = os.path.join(SCRIPT_DIR, "photo_progress.json")
PHOTOS_DIR = os.path.join(PROJECT_ROOT, "public", "photos")

SLEEP_INTERVAL = 0.1
MIN_FILE_SIZE = 1024  # 1KB


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


def download_photo(photo_reference, dest_path, api_key):
    """Download a photo via Places API. Returns (success, error_string)."""
    url = (
        f"https://places.googleapis.com/v1/{photo_reference}/media"
        f"?maxWidthPx=800&key={api_key}"
    )
    req = urllib.request.Request(url)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            with open(dest_path, "wb") as f:
                f.write(data)
            return True, None
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return False, f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return False, str(e)


def main():
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        print("ERROR: GOOGLE_PLACES_API_KEY environment variable is not set.")
        sys.exit(1)

    # Load kid-friendly shops
    shops = load_json(KID_FRIENDLY_PATH)
    if not shops:
        print(f"ERROR: {KID_FRIENDLY_PATH} not found or empty.")
        sys.exit(1)

    # Create photos directory
    os.makedirs(PHOTOS_DIR, exist_ok=True)

    # Load progress (set of already-processed place_ids)
    progress_list = load_json(PROGRESS_PATH, [])
    processed_ids = set(progress_list)

    total = len(shops)
    count_downloaded = 0
    count_skipped = 0
    count_failed = 0

    print(f"Total shops in kid_friendly.json: {total}")
    print(f"Already processed (in progress file): {len(processed_ids)}")
    print()

    for i, shop in enumerate(shops):
        place_id = shop.get("place_id", "")
        shop_name = shop.get("name", place_id)
        photo_reference = shop.get("photo_reference", "")
        dest_path = os.path.join(PHOTOS_DIR, f"{place_id}.jpg")
        image_url = f"/photos/{place_id}.jpg"

        # Skip if no photo_reference
        if not photo_reference:
            print(f"  [{i+1}/{total}] {shop_name} -> skipped (no photo_reference)")
            count_skipped += 1
            processed_ids.add(place_id)
            continue

        # Skip if file already exists and is large enough
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > MIN_FILE_SIZE:
            shop["image_url"] = image_url
            print(f"  [{i+1}/{total}] {shop_name} -> skipped (file exists)")
            count_skipped += 1
            processed_ids.add(place_id)
            continue

        # Skip if already processed via progress file (e.g. previous failed attempt)
        if place_id in processed_ids:
            # Still set image_url if file exists
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > MIN_FILE_SIZE:
                shop["image_url"] = image_url
            print(f"  [{i+1}/{total}] {shop_name} -> skipped (already processed)")
            count_skipped += 1
            continue

        # Download
        ok, err = download_photo(photo_reference, dest_path, api_key)

        if ok:
            shop["image_url"] = image_url
            print(f"  [{i+1}/{total}] {shop_name} -> downloaded")
            count_downloaded += 1
        else:
            print(f"  [{i+1}/{total}] {shop_name} -> failed: {err}")
            count_failed += 1

        processed_ids.add(place_id)
        time.sleep(SLEEP_INTERVAL)

    # Save progress
    save_json(PROGRESS_PATH, list(processed_ids))

    # Save updated kid_friendly.json with image_url populated
    save_json(KID_FRIENDLY_PATH, shops)

    # Summary
    print()
    print("=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"  Total shops       : {total}")
    print(f"  Downloaded        : {count_downloaded}")
    print(f"  Skipped           : {count_skipped}")
    print(f"  Failed            : {count_failed}")
    print()


if __name__ == "__main__":
    main()
