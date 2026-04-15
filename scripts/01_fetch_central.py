"""
中央区15地点を Nearby Search で一括取得する。

出力: scripts/raw_central.json (place_id重複はそのまま、後段で除外)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

API_URL = "https://places.googleapis.com/v1/places:searchNearby"
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.primaryType",
    "places.types",
])

POINTS = [
    {"name": "円山",          "lat": 43.055, "lng": 141.316},
    {"name": "宮の森",        "lat": 43.063, "lng": 141.303},
    {"name": "知事公館",      "lat": 43.060, "lng": 141.324},
    {"name": "札幌駅南",      "lat": 43.067, "lng": 141.350},
    {"name": "大通公園",      "lat": 43.061, "lng": 141.350},
    {"name": "狸小路",        "lat": 43.056, "lng": 141.353},
    {"name": "ススキノ",      "lat": 43.055, "lng": 141.352},
    {"name": "中島公園",      "lat": 43.050, "lng": 141.351},
    {"name": "西11丁目",      "lat": 43.055, "lng": 141.334},
    {"name": "山鼻西線",      "lat": 43.048, "lng": 141.338},
    {"name": "伏見",          "lat": 43.042, "lng": 141.327},
    {"name": "藻岩山麓",      "lat": 43.040, "lng": 141.332},
    {"name": "幌西",          "lat": 43.049, "lng": 141.322},
    {"name": "南円山",        "lat": 43.048, "lng": 141.318},
    {"name": "北円山",        "lat": 43.064, "lng": 141.316},
]
RADIUS = 800.0

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_PATH = SCRIPT_DIR / "raw_central.json"


def load_key() -> str:
    k = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if not k:
        print("ERROR: GOOGLE_PLACES_API_KEY 未設定", file=sys.stderr)
        sys.exit(1)
    return k


def fetch(api_key: str, point: dict) -> list[dict]:
    body = {
        "includedTypes": ["restaurant", "cafe", "bakery", "bar"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": point["lat"], "longitude": point["lng"]},
                "radius": RADIUS,
            }
        },
        "languageCode": "ja",
        "regionCode": "JP",
    }
    req = request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
    )
    try:
        with request.urlopen(req, timeout=20) as res:
            payload = json.loads(res.read().decode("utf-8"))
            return payload.get("places", []) or []
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"   [API {e.code}] {body[:200]}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"   [err] {e}", file=sys.stderr)
        return []


def main() -> None:
    key = load_key()
    all_places: list[dict] = []
    for i, p in enumerate(POINTS, 1):
        print(f"[{i}/{len(POINTS)}] {p['name']} ({p['lat']},{p['lng']})")
        places = fetch(key, p)
        print(f"   → {len(places)} 件")
        for pl in places:
            pl["_fetched_at"] = p["name"]
        all_places.extend(places)
        time.sleep(0.2)

    OUT_PATH.write_text(
        json.dumps(all_places, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print()
    print(f"出力: {OUT_PATH}")
    print(f"総レコード: {len(all_places)} 件 (重複含む)")
    unique_ids = {p.get("id") for p in all_places if p.get("id")}
    print(f"ユニーク: {len(unique_ids)} 件")


if __name__ == "__main__":
    main()
