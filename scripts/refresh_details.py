"""
data/shops.json の各店舗について Place Details API を呼び
name / address / lat / lng / primaryType を権威データで上書きし、
tabelog_url を googleMapsUri に置き換える。

使い方:
    export GOOGLE_PLACES_API_KEY="AIza..."
    python3 scripts/refresh_details.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parent.parent
SHOPS_PATH = ROOT / "data" / "shops.json"

# Field Mask: Essentials + Pro
FIELD_MASK = ",".join([
    "id",
    "displayName",
    "formattedAddress",
    "location",
    "primaryType",
    "types",
    "googleMapsUri",
    "websiteUri",
    "businessStatus",
])

SLEEP_SEC = 0.3  # API レート制限対策


def load_key() -> str:
    k = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if not k:
        print("ERROR: GOOGLE_PLACES_API_KEY が未設定です。", file=sys.stderr)
        sys.exit(1)
    return k


def fetch_detail(api_key: str, place_id: str) -> dict[str, Any] | None:
    url = f"https://places.googleapis.com/v1/places/{place_id}?languageCode=ja&regionCode=JP"
    req = request.Request(
        url,
        method="GET",
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
    )
    try:
        with request.urlopen(req, timeout=20) as res:
            return json.loads(res.read().decode("utf-8"))
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"   [API {e.code}] {body[:200]}", file=sys.stderr)
        return None
    except error.URLError as e:
        print(f"   [接続失敗] {e.reason}", file=sys.stderr)
        return None


def determine_area(address: str, lat: float) -> str:
    if "宮ケ丘" in address or "宮の森" in address:
        return "宮の森"
    return "円山"


def main() -> None:
    api_key = load_key()

    shops = json.loads(SHOPS_PATH.read_text(encoding="utf-8"))
    print(f"対象: {len(shops)} 店舗")
    print()

    updated = 0
    closed = 0
    errors = 0

    for i, s in enumerate(shops, 1):
        pid = s.get("place_id")
        old_name = s.get("name", "")
        print(f"[{i}/{len(shops)}] {old_name}")

        if not pid:
            print("   SKIP: place_idなし")
            continue

        detail = fetch_detail(api_key, pid)
        time.sleep(SLEEP_SEC)

        if not detail:
            print("   失敗")
            errors += 1
            continue

        # 権威データ抽出
        new_name = (detail.get("displayName") or {}).get("text") or old_name
        new_address = detail.get("formattedAddress") or s.get("address", "")
        loc = detail.get("location") or {}
        new_lat = loc.get("latitude", s["lat"])
        new_lng = loc.get("longitude", s["lng"])
        new_ptype = detail.get("primaryType") or ""
        gmap_uri = detail.get("googleMapsUri") or ""
        website = detail.get("websiteUri") or ""
        status = detail.get("businessStatus") or ""

        # 変更検出
        changes = []
        if new_name != old_name:
            changes.append(f"name: {old_name} → {new_name}")
        if abs((new_lat or 0) - s["lat"]) > 1e-6 or abs((new_lng or 0) - s["lng"]) > 1e-6:
            changes.append(f"location: ({s['lat']:.5f},{s['lng']:.5f}) → ({new_lat:.5f},{new_lng:.5f})")
        old_url = s.get("tabelog_url", "")
        if gmap_uri and old_url != gmap_uri:
            changes.append(f"url → googleMapsUri")

        # 更新
        s["name"] = new_name
        s["lat"] = new_lat
        s["lng"] = new_lng
        s["area"] = determine_area(new_address, new_lat or 0)
        if gmap_uri:
            s["tabelog_url"] = gmap_uri  # フィールド名はそのまま、中身だけ置換
        if website:
            s["website_uri"] = website

        if status and status != "OPERATIONAL":
            closed += 1
            print(f"   ⚠️  businessStatus: {status}")

        if status == "OPERATIONAL":
            print(f"   ✓ 営業中")
        print(f"   住所: {new_address}")
        print(f"   座標: {new_lat}, {new_lng}")
        print(f"   primaryType: {new_ptype}")
        print(f"   GoogleMaps: {gmap_uri}")
        if website:
            print(f"   Website: {website}")
        if changes:
            print(f"   変更: " + " / ".join(changes))
        updated += 1
        print()

    SHOPS_PATH.write_text(
        json.dumps(shops, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=" * 40)
    print(f"更新: {updated} 件")
    print(f"営業終了/閉店疑い: {closed} 件")
    print(f"エラー: {errors} 件")
    print(f"保存: {SHOPS_PATH}")


if __name__ == "__main__":
    main()
