"""選定された店舗の Place Details + 写真5枚を Places API (New) で取得する。
- 各店舗の outputs/instagram/YYYYMMDD/shop_{id}/raw/ に保存
- shop_{id}/details.json に住所・営業時間・評価などを保存
- logs/cost_YYYYMM.json に使用量を記録 (上限 $150 で停止)
"""
import json
import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "instagram"
COST_DIR = ROOT / "logs"
ENV_FILE = ROOT / ".env.local"

PHOTOS_PER_SHOP = 5
MONTHLY_BUDGET_USD = 150.0
DETAILS_COST_USD = 0.005   # Essentials SKU
PHOTO_COST_USD = 0.007


def load_env() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("GOOGLE_PLACES_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GOOGLE_PLACES_API_KEY not found in .env.local")


def load_cost(month_key: str) -> dict:
    f = COST_DIR / f"cost_{month_key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"month": month_key, "details_calls": 0, "photo_calls": 0, "total_usd": 0.0}


def save_cost(month_key: str, data: dict) -> None:
    (COST_DIR / f"cost_{month_key}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def http_get(url: str, headers: dict) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch_details(place_id: str, api_key: str) -> dict:
    url = f"https://places.googleapis.com/v1/places/{place_id}?languageCode=ja&regionCode=JP"
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "id,displayName,formattedAddress,rating,userRatingCount,"
                            "regularOpeningHours,nationalPhoneNumber,websiteUri,photos",
    }
    raw = http_get(url, headers)
    return json.loads(raw)


def fetch_photo(photo_name: str, api_key: str, max_px: int = 1200) -> bytes:
    url = (f"https://places.googleapis.com/v1/{photo_name}/media"
           f"?maxWidthPx={max_px}&key={api_key}")
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read()


def main() -> None:
    today = date.today().strftime("%Y%m%d")
    month_key = date.today().strftime("%Y%m")
    day_dir = OUT_DIR / today
    selection_file = day_dir / "selected.json"
    if not selection_file.exists():
        raise SystemExit(f"先に 01_select_shops.py を実行してください: {selection_file}")

    api_key = load_env()
    cost = load_cost(month_key)

    if cost["total_usd"] >= MONTHLY_BUDGET_USD:
        raise SystemExit(f"月次予算超過 ${cost['total_usd']:.2f} >= ${MONTHLY_BUDGET_USD}")

    selected = json.loads(selection_file.read_text(encoding="utf-8"))
    for shop in selected:
        sid = shop["id"]
        shop_dir = day_dir / f"shop_{sid}"
        raw_dir = shop_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        print(f"[{sid}] {shop['name']}")

        details = fetch_details(shop["place_id"], api_key)
        cost["details_calls"] += 1
        cost["total_usd"] += DETAILS_COST_USD

        (shop_dir / "details.json").write_text(
            json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        photos = details.get("photos", [])[:PHOTOS_PER_SHOP]
        for i, p in enumerate(photos, start=1):
            if cost["total_usd"] >= MONTHLY_BUDGET_USD:
                print("  予算上限到達のため中断")
                save_cost(month_key, cost)
                sys.exit(0)
            try:
                img = fetch_photo(p["name"], api_key)
                (raw_dir / f"{i:02d}.jpg").write_bytes(img)
                cost["photo_calls"] += 1
                cost["total_usd"] += PHOTO_COST_USD
                print(f"  写真 {i}/{len(photos)} 保存")
            except Exception as e:
                print(f"  写真 {i} エラー: {e}")

        save_cost(month_key, cost)

    print(f"\n累計コスト: ${cost['total_usd']:.4f} / ${MONTHLY_BUDGET_USD}")


if __name__ == "__main__":
    main()
