"""image_url が空 & place_id 持ちの店舗だけ画像を取得する。
Text Search を省略して Place Details (photos field) → Place Photos の2段で済ませる。

コスト概算:
  Place Details Pro (photos): $0.020
  Place Photos: $0.007
  → 1店 $0.027 / 200店 $5.40
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parent.parent
SHOPS_PATH = ROOT / "data" / "shops.json"
PHOTOS_DIR = ROOT / "public" / "photos"
ENV_FILE = ROOT / ".env.local"

DETAILS_URL = "https://places.googleapis.com/v1/places/{}"
PHOTOS_URL = "https://places.googleapis.com/v1/{}/media"
SLEEP = 0.3
MAX_PER_RUN = 250  # 一度の実行で処理する最大件数


def load_key() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("GOOGLE_PLACES_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GOOGLE_PLACES_API_KEY not found in .env.local")


def get_photo_name(api_key: str, place_id: str) -> str | None:
    url = DETAILS_URL.format(place_id) + "?languageCode=ja&regionCode=JP"
    req = request.Request(
        url,
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "id,photos",
        },
    )
    try:
        with request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        photos = data.get("photos") or []
        if not photos:
            return None
        return photos[0].get("name")
    except error.HTTPError as e:
        print(f"  [HTTP {e.code}] {e.read().decode()[:120]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [err] {e}", file=sys.stderr)
        return None


def download_photo(api_key: str, photo_name: str, filename: str) -> str | None:
    url = PHOTOS_URL.format(photo_name) + f"?maxWidthPx=800&key={api_key}"
    try:
        with request.urlopen(url, timeout=30) as r:
            data = r.read()
    except Exception as e:
        print(f"  [photo err] {e}", file=sys.stderr)
        return None

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    path = PHOTOS_DIR / filename
    path.write_bytes(data)
    return f"/photos/{filename}"


def main() -> None:
    api_key = load_key()
    shops = json.loads(SHOPS_PATH.read_text(encoding="utf-8"))

    targets = [
        s for s in shops
        if not s.get("image_url") and s.get("place_id")
    ]
    print(f"対象: {len(targets)} 店 (image_url なし & place_id 持ち)")

    if not targets:
        print("対象なし")
        return

    if len(targets) > MAX_PER_RUN:
        print(f"⚠️  上限 {MAX_PER_RUN} 件で打ち切り（再実行で続き）")
        targets = targets[:MAX_PER_RUN]

    updated = 0
    no_photo = 0
    failed = 0

    try:
        for i, s in enumerate(targets, 1):
            pid = s["place_id"]
            print(f"[{i}/{len(targets)}] {s['name']}", end="", flush=True)
            photo_name = get_photo_name(api_key, pid)
            time.sleep(SLEEP)
            if not photo_name:
                print(" → 写真なし")
                no_photo += 1
                continue
            filename = f"g_pid_{pid[:30]}.jpg"
            img_url = download_photo(api_key, photo_name, filename)
            time.sleep(SLEEP)
            if img_url:
                s["image_url"] = img_url
                updated += 1
                print(f" → {img_url}")
            else:
                print(" → DL失敗")
                failed += 1

            # 100件ごとに途中保存
            if i % 100 == 0:
                SHOPS_PATH.write_text(
                    json.dumps(shops, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"  💾 中間保存 ({updated}件更新済み)")
    finally:
        SHOPS_PATH.write_text(
            json.dumps(shops, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    cost = (updated + no_photo + failed) * 0.020 + updated * 0.007
    print(f"\n✅ 更新: {updated} / 写真なし: {no_photo} / 失敗: {failed}")
    print(f"   概算コスト: ${cost:.2f}")


if __name__ == "__main__":
    main()
