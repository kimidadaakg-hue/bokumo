"""全 559 店舗の Place Details を取得して shops.json に address/rating/rating_count/hours を追記。
Places API (New) Essentials SKU: $0.005/件 → 約 $2.80 (無料枠 $200 内)
レート制限対策で 0.1秒スリープ。
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOPS = ROOT / "data" / "shops.json"
ENV = ROOT / ".env.local"


def load_key() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("GOOGLE_PLACES_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GOOGLE_PLACES_API_KEY not found")


def fetch(place_id: str, key: str) -> dict:
    url = f"https://places.googleapis.com/v1/places/{place_id}?languageCode=ja&regionCode=JP"
    req = urllib.request.Request(url, headers={
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "formattedAddress,rating,userRatingCount,regularOpeningHours,nationalPhoneNumber,websiteUri",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> None:
    shops = json.loads(SHOPS.read_text(encoding="utf-8"))
    key = load_key()

    updated = 0
    failed = []
    for i, shop in enumerate(shops):
        if not shop.get("place_id"):
            continue
        # 既に取得済みならスキップ (再実行用)
        if shop.get("address") and shop.get("hours") is not None:
            continue
        try:
            d = fetch(shop["place_id"], key)
            shop["address"] = d.get("formattedAddress", "")
            shop["rating"] = d.get("rating", 0)
            shop["rating_count"] = d.get("userRatingCount", 0)
            hours = d.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
            shop["hours"] = hours
            shop["phone"] = d.get("nationalPhoneNumber", "")
            shop["website"] = d.get("websiteUri", "")
            updated += 1
            if updated % 20 == 0:
                print(f"  {updated} 件更新 (進捗 {i+1}/{len(shops)})")
                # 進捗保存
                SHOPS.write_text(json.dumps(shops, ensure_ascii=False, indent=2), encoding="utf-8")
            time.sleep(0.1)
        except Exception as e:
            failed.append((shop["id"], str(e)))
            print(f"  [{shop['id']}] {shop['name']} エラー: {e}")

    SHOPS.write_text(json.dumps(shops, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完了: {updated} 件更新 / 失敗 {len(failed)} 件")
    if failed:
        for sid, err in failed[:10]:
            print(f"  [{sid}] {err}")


if __name__ == "__main__":
    main()
