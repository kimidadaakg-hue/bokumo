"""
Google Places API (New) を使って
札幌市・円山/宮の森エリアの飲食店を取得する。

使い方:
    export GOOGLE_PLACES_API_KEY="YOUR_KEY"
    python scripts/fetch_shops.py

出力:
    scripts/shops_raw.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error, request

API_URL = "https://places.googleapis.com/v1/places:searchNearby"

# 取得フィールド(Essentials SKU のみ)
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.primaryType",
        "places.types",
    ]
)

# 取得エリア (中心 + 半径 m)
AREAS = [
    {"name": "円山",   "lat": 43.055, "lng": 141.316, "radius": 800.0},
    {"name": "宮の森", "lat": 43.070, "lng": 141.308, "radius": 800.0},
]

# 飲食店として扱う type (restaurant / cafe / food 系)
FOOD_TYPES = {
    "restaurant",
    "cafe",
    "bakery",
    "bar",
    "meal_takeaway",
    "meal_delivery",
    "food",
    "japanese_restaurant",
    "italian_restaurant",
    "french_restaurant",
    "chinese_restaurant",
    "korean_restaurant",
    "american_restaurant",
    "seafood_restaurant",
    "sushi_restaurant",
    "ramen_restaurant",
    "steak_house",
    "pizza_restaurant",
    "hamburger_restaurant",
    "sandwich_shop",
    "coffee_shop",
    "dessert_shop",
    "ice_cream_shop",
    "brunch_restaurant",
    "breakfast_restaurant",
}

# チェーン店除外ワード (小文字で部分一致判定)
CHAIN_KEYWORDS = [
    # カフェチェーン
    "starbucks", "スターバックス", "スタバ",
    "doutor", "ドトール",
    "tully", "タリーズ",
    "excelsior", "エクセルシオール",
    "veloce", "ベローチェ",
    "pronto", "プロント",
    "komeda", "コメダ",
    "saint marc", "サンマルク",
    "ueshima", "上島珈琲",
    "caffe ciao presso",
    # ファストフード
    "mcdonald", "マクドナルド", "マック",
    "kfc", "ケンタッキー",
    "burger king", "バーガーキング",
    "mos burger", "モスバーガー", "モス",
    "lotteria", "ロッテリア",
    "freshness", "フレッシュネス",
    "subway", "サブウェイ",
    "first kitchen", "ファーストキッチン",
    # 牛丼・定食
    "yoshinoya", "吉野家",
    "sukiya", "すき家",
    "matsuya", "松屋",
    "nakau", "なか卯",
    "ootoya", "大戸屋",
    "yayoiken", "やよい軒",
    # ラーメン
    "ichiran", "一蘭",
    "ippudo", "一風堂",
    "tenkaippin", "天下一品",
    "kourakuen", "幸楽苑",
    "hidakaya", "日高屋",
    # 居酒屋
    "watami", "ワタミ", "和民",
    "shirokiya", "白木屋",
    "kinnokura", "金の蔵",
    "torikizoku", "鳥貴族",
    "isomaru", "磯丸",
    # ファミレス
    "gusto", "ガスト",
    "saizeriya", "サイゼリヤ",
    "denny", "デニーズ",
    "jonathan", "ジョナサン",
    "bamiyan", "バーミヤン",
    "royal host", "ロイヤルホスト",
    "coco", "ココス",
    # 寿司・回転寿司
    "sushiro", "スシロー",
    "kura sushi", "くら寿司",
    "kappa", "かっぱ寿司",
    "hamazushi", "はま寿司",
    "ganko", "がんこ",
    # その他
    "ootoro", "大トロ",
    "ootoya",
    "cocoichi", "ココイチ", "カレーハウスco",
    "marugame", "丸亀製麺",
    "hanamaru", "はなまるうどん",
    "ringer hut", "リンガーハット",
    "ootoya",
    "pepper lunch", "ペッパーランチ",
    "ootoya",
    "mister donut", "ミスタードーナツ", "ミスド",
    "krispy kreme", "クリスピー",
    "baskin", "サーティワン",
]


def load_api_key() -> str:
    key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if not key:
        print(
            "ERROR: 環境変数 GOOGLE_PLACES_API_KEY が設定されていません。\n"
            "  例) export GOOGLE_PLACES_API_KEY='AIza...'",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def fetch_area(api_key: str, area: dict[str, Any]) -> list[dict[str, Any]]:
    """指定エリアの周辺検索を実行して places 配列を返す。"""
    body = {
        "includedTypes": ["restaurant", "cafe", "bakery", "bar"],
        "maxResultCount": 20,  # Nearby Search の上限
        "locationRestriction": {
            "circle": {
                "center": {"latitude": area["lat"], "longitude": area["lng"]},
                "radius": area["radius"],
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
    except error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: API {e.code}: {msg}", file=sys.stderr)
        sys.exit(1)
    except error.URLError as e:
        print(f"ERROR: 接続失敗: {e.reason}", file=sys.stderr)
        sys.exit(1)

    return payload.get("places", [])


def is_food_place(place: dict[str, Any]) -> bool:
    """飲食店に該当する type を持っているか。"""
    types = set(place.get("types", []) or [])
    primary = place.get("primaryType")
    if primary:
        types.add(primary)
    return bool(types & FOOD_TYPES)


def is_chain(name: str) -> bool:
    """名前がチェーン店ワードにマッチするか (部分一致・大文字小文字無視)。"""
    n = name.lower()
    return any(kw.lower() in n for kw in CHAIN_KEYWORDS)


def normalize(place: dict[str, Any]) -> dict[str, Any] | None:
    """API レスポンスを出力フォーマットに整形。"""
    place_id = place.get("id")
    display = place.get("displayName") or {}
    name = display.get("text") if isinstance(display, dict) else None
    address = place.get("formattedAddress")
    loc = place.get("location") or {}
    lat = loc.get("latitude")
    lng = loc.get("longitude")
    ptype = place.get("primaryType") or (
        (place.get("types") or [None])[0] if place.get("types") else None
    )

    if not (place_id and name and lat is not None and lng is not None):
        return None

    return {
        "place_id": place_id,
        "name": name,
        "address": address or "",
        "lat": lat,
        "lng": lng,
        "type": ptype or "",
    }


def main() -> None:
    api_key = load_api_key()

    all_places: list[dict[str, Any]] = []
    for area in AREAS:
        print(f"[fetch] {area['name']} (lat={area['lat']}, lng={area['lng']}, r={area['radius']}m)")
        places = fetch_area(api_key, area)
        print(f"  → {len(places)} 件取得")
        all_places.extend(places)

    seen_ids: set[str] = set()
    shops: list[dict[str, Any]] = []
    skipped_chain = 0
    skipped_nonfood = 0
    skipped_dup = 0

    for p in all_places:
        row = normalize(p)
        if not row:
            continue
        if row["place_id"] in seen_ids:
            skipped_dup += 1
            continue
        if not is_food_place(p):
            skipped_nonfood += 1
            continue
        if is_chain(row["name"]):
            skipped_chain += 1
            continue
        seen_ids.add(row["place_id"])
        shops.append(row)

    out_path = Path(__file__).resolve().parent / "shops_raw.json"
    out_path.write_text(
        json.dumps(shops, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"出力: {out_path}")
    print(f"  採用 : {len(shops)} 件")
    print(f"  除外 : チェーン={skipped_chain} / 非飲食={skipped_nonfood} / 重複={skipped_dup}")


if __name__ == "__main__":
    main()
