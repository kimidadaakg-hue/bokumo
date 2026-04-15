"""
data/shops.json の各店舗について
Google Places Text Search で place_id + photo を取得し、
Place Photos API で画像をダウンロードする。

使い方:
    export GOOGLE_PLACES_API_KEY="AIza..."
    python3 scripts/fetch_google_photos.py

コスト:
    Text Search Pro: $35/1000 (place_id+photos取得)
    Place Photos: $7/1000 (画像DL)
    3888店 → 約 $163 ($200/月 無料枠内)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parent.parent
SHOPS_PATH = ROOT / "data" / "shops.json"
PHOTOS_DIR = ROOT / "public" / "photos"
PROGRESS_PATH = Path(__file__).resolve().parent / "photo_progress.json"

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
TEXT_SEARCH_FIELDS = "places.id,places.photos"

SLEEP_SEARCH = 0.15  # Text Search 間隔
SLEEP_PHOTO = 0.1    # Photo DL 間隔


def load_key() -> str:
    k = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if not k:
        print("ERROR: GOOGLE_PLACES_API_KEY 未設定", file=sys.stderr)
        sys.exit(1)
    return k


def load_progress() -> set[str]:
    if PROGRESS_PATH.exists():
        try:
            return set(json.loads(PROGRESS_PATH.read_text("utf-8")))
        except Exception:
            pass
    return set()


def save_progress(done: set[str]) -> None:
    PROGRESS_PATH.write_text(
        json.dumps(sorted(done), ensure_ascii=False), encoding="utf-8"
    )


def text_search(api_key: str, name: str, lat: float, lng: float) -> dict | None:
    """Text Search で店舗を検索し、place_id と photo_name を返す。"""
    body = {
        "textQuery": name,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 200.0,
            }
        },
        "maxResultCount": 1,
        "languageCode": "ja",
        "regionCode": "JP",
    }
    req = request.Request(
        TEXT_SEARCH_URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": TEXT_SEARCH_FIELDS,
        },
    )
    try:
        with request.urlopen(req, timeout=15) as res:
            payload = json.loads(res.read().decode("utf-8"))
            places = payload.get("places") or []
            if not places:
                return None
            p = places[0]
            photos = p.get("photos") or []
            photo_name = photos[0].get("name", "") if photos else ""
            return {"place_id": p.get("id", ""), "photo_name": photo_name}
    except error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        print(f"    [Search {e.code}] {body_err[:150]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"    [Search err] {e}", file=sys.stderr)
        return None


def download_photo(api_key: str, photo_name: str, filename: str) -> str:
    """Place Photos API で画像をダウンロード。戻り値: 相対URL。"""
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = PHOTOS_DIR / filename

    if out_file.exists() and out_file.stat().st_size > 1000:
        return f"/photos/{filename}"

    url = (
        f"https://places.googleapis.com/v1/{photo_name}/media"
        f"?maxWidthPx=800&key={api_key}"
    )
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=30) as res:
            content = res.read()
            if len(content) < 500:
                return ""
            out_file.write_bytes(content)
            return f"/photos/{filename}"
    except Exception as e:
        print(f"    [Photo err] {e}", file=sys.stderr)
        return ""


def main() -> None:
    api_key = load_key()
    shops = json.loads(SHOPS_PATH.read_text("utf-8"))
    done = load_progress()

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("BOKUMO fetch_google_photos.py")
    print("=" * 50)
    print(f"対象: {len(shops)} 件 / 処理済み: {len(done)} 件")
    print()

    updated = 0
    failed = 0
    skipped = 0

    try:
        for i, s in enumerate(shops, 1):
            shop_key = s.get("hotpepper_id") or s.get("name", str(s.get("id")))

            if shop_key in done:
                skipped += 1
                continue

            name = s.get("name", "")
            lat = s.get("lat", 0)
            lng = s.get("lng", 0)

            print(f"[{i}/{len(shops)}] {name}", end="", flush=True)

            # Text Search
            result = text_search(api_key, name, lat, lng)
            time.sleep(SLEEP_SEARCH)

            if not result or not result.get("photo_name"):
                print(" → 写真なし")
                done.add(shop_key)
                failed += 1
                continue

            # Photo DL
            filename = f"g_{shop_key}.jpg"
            img_url = download_photo(api_key, result["photo_name"], filename)
            time.sleep(SLEEP_PHOTO)

            if img_url:
                s["image_url"] = img_url
                updated += 1
                print(f" → {img_url}")
            else:
                print(" → DL失敗")
                failed += 1

            done.add(shop_key)

            # 50件ごとに保存
            if updated % 50 == 0 and updated > 0:
                SHOPS_PATH.write_text(
                    json.dumps(shops, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                save_progress(done)
                print(f"    [保存: {updated}件更新済み]")

    except KeyboardInterrupt:
        print("\n中断")

    # 最終保存
    SHOPS_PATH.write_text(
        json.dumps(shops, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    save_progress(done)

    print()
    print("=" * 50)
    print(f"  写真更新: {updated} 件")
    print(f"  写真なし/失敗: {failed} 件")
    print(f"  スキップ(済): {skipped} 件")
    print(f"  出力: {SHOPS_PATH}")


if __name__ == "__main__":
    main()
