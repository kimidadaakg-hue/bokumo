"""
Google Places API (New) Nearby Search を使って
札幌市・円山/宮の森エリアの飲食店リストを取得する。

使い方:
    export GOOGLE_PLACES_API_KEY="AIza..."
    python3 scripts/get_shops.py

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

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.primaryType",
    "places.types",
    "places.photos",
])

AREAS = [
    # --- 中央区 ---
    {"name": "円山",       "lat": 43.055, "lng": 141.316, "radius": 800.0},
    {"name": "宮の森",      "lat": 43.070, "lng": 141.308, "radius": 800.0},
    {"name": "札幌駅南",    "lat": 43.067, "lng": 141.350, "radius": 800.0},
    {"name": "大通",       "lat": 43.060, "lng": 141.350, "radius": 800.0},
    {"name": "ススキノ",    "lat": 43.055, "lng": 141.353, "radius": 800.0},
    {"name": "中島公園",    "lat": 43.048, "lng": 141.351, "radius": 800.0},
    {"name": "西11丁目",   "lat": 43.055, "lng": 141.334, "radius": 800.0},
    {"name": "山鼻西線",    "lat": 43.045, "lng": 141.340, "radius": 800.0},
    {"name": "伏見",       "lat": 43.042, "lng": 141.327, "radius": 800.0},
    {"name": "行啓通",     "lat": 43.048, "lng": 141.347, "radius": 800.0},
    {"name": "幌西",       "lat": 43.049, "lng": 141.322, "radius": 800.0},
    {"name": "南円山",     "lat": 43.048, "lng": 141.318, "radius": 800.0},
    {"name": "北円山",     "lat": 43.064, "lng": 141.316, "radius": 800.0},
    # --- 北区 (bbox北端内) ---
    {"name": "北24条",     "lat": 43.090, "lng": 141.346, "radius": 800.0},
    {"name": "新川",       "lat": 43.090, "lng": 141.325, "radius": 800.0},
    {"name": "北大北",     "lat": 43.078, "lng": 141.345, "radius": 800.0},
    # --- 東区 ---
    {"name": "苗穂",       "lat": 43.060, "lng": 141.378, "radius": 800.0},
    {"name": "東区役所前",  "lat": 43.075, "lng": 141.371, "radius": 800.0},
    {"name": "環状通東",    "lat": 43.065, "lng": 141.375, "radius": 800.0},
    # --- 白石区 ---
    {"name": "白石駅",     "lat": 43.050, "lng": 141.395, "radius": 800.0},
    {"name": "東札幌",     "lat": 43.052, "lng": 141.378, "radius": 800.0},
    {"name": "菊水",       "lat": 43.060, "lng": 141.366, "radius": 800.0},
    # --- 豊平区 ---
    {"name": "学園前",     "lat": 43.040, "lng": 141.362, "radius": 800.0},
    {"name": "美園",       "lat": 43.043, "lng": 141.377, "radius": 800.0},
    {"name": "月寒",       "lat": 43.040, "lng": 141.395, "radius": 800.0},
    # --- 西区 (bbox東端) ---
    {"name": "琴似",       "lat": 43.075, "lng": 141.302, "radius": 800.0},
    {"name": "二十四軒",    "lat": 43.070, "lng": 141.313, "radius": 800.0},
    {"name": "発寒南東",    "lat": 43.080, "lng": 141.282, "radius": 800.0},
    # --- 南区 (bbox南端) ---
    {"name": "藻岩下",     "lat": 43.030, "lng": 141.332, "radius": 800.0},
    {"name": "真駒内北",    "lat": 43.010, "lng": 141.356, "radius": 800.0},
]

# 飲食店とみなす type (restaurant/cafe/food 系)
FOOD_TYPES = {
    "restaurant", "cafe", "bakery", "bar", "meal_takeaway", "meal_delivery",
    "food", "japanese_restaurant", "italian_restaurant", "french_restaurant",
    "chinese_restaurant", "korean_restaurant", "american_restaurant",
    "seafood_restaurant", "sushi_restaurant", "ramen_restaurant", "steak_house",
    "pizza_restaurant", "hamburger_restaurant", "sandwich_shop", "coffee_shop",
    "dessert_shop", "dessert_restaurant", "ice_cream_shop", "brunch_restaurant",
    "breakfast_restaurant", "thai_restaurant", "indian_restaurant",
    "mexican_restaurant", "vegetarian_restaurant", "vegan_restaurant",
    "asian_restaurant", "mediterranean_restaurant", "spanish_restaurant",
    "japanese_izakaya_restaurant", "yakitori_restaurant", "yakiniku_restaurant",
    "udon_noodle_shop", "soba_noodle_shop", "cake_shop", "pastry_shop",
    "fine_dining_restaurant", "western_restaurant", "family_restaurant",
    "food_store", "tea_house", "juice_shop",
}

# チェーン店除外ワード (小文字で部分一致)
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
    # ファストフード
    "mcdonald", "マクドナルド", "マック",
    "kfc", "ケンタッキー",
    "burger king", "バーガーキング",
    "mos burger", "モスバーガー", "モス",
    "lotteria", "ロッテリア",
    "freshness", "フレッシュネス",
    "subway", "サブウェイ",
    "first kitchen", "ファーストキッチン",
    # 牛丼/定食
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
    "山頭火",
    # 居酒屋
    "watami", "ワタミ", "和民",
    "shirokiya", "白木屋",
    "torikizoku", "鳥貴族",
    "isomaru", "磯丸",
    "串鳥",
    "つぼ八",
    # ファミレス
    "gusto", "ガスト",
    "saizeriya", "サイゼリヤ",
    "denny", "デニーズ",
    "jonathan", "ジョナサン",
    "bamiyan", "バーミヤン",
    "royal host", "ロイヤルホスト",
    "coco's", "ココス",
    "びっくりドンキー",
    "ヴィクトリアステーション",
    # 回転寿司
    "sushiro", "スシロー",
    "kura sushi", "くら寿司",
    "kappa", "かっぱ寿司",
    "hamazushi", "はま寿司",
    "回転寿しトリトン",
    "根室花まる",
    # その他
    "cocoichi", "ココイチ",
    "marugame", "丸亀製麺",
    "hanamaru", "はなまるうどん",
    "ringer hut", "リンガーハット",
    "pepper lunch", "ペッパーランチ",
    "mister donut", "ミスタードーナツ", "ミスド",
    "krispy kreme", "クリスピー",
    "baskin", "サーティワン",
    # 北海道ローカルチェーン
    "六花亭",
    "きのとや",
    "もりもと",
    "ロイズ", "royce",
    "北菓楼",
    "とんでん",
    "暖龍",
    "sama",
    "かつ徳",
]


def load_key() -> str:
    k = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if not k:
        print("ERROR: 環境変数 GOOGLE_PLACES_API_KEY が未設定です。", file=sys.stderr)
        sys.exit(1)
    return k


def fetch_area(api_key: str, area: dict[str, Any]) -> list[dict[str, Any]]:
    body = {
        "includedTypes": ["restaurant", "cafe", "bakery", "bar"],
        "maxResultCount": 20,
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
            return (json.loads(res.read().decode("utf-8"))).get("places", []) or []
    except error.HTTPError as e:
        print(f"   [API {e.code}] {e.read().decode('utf-8', errors='replace')[:200]}",
              file=sys.stderr)
        return []
    except Exception as e:
        print(f"   [err] {e}", file=sys.stderr)
        return []


def is_food(place: dict) -> bool:
    types = set(place.get("types") or [])
    if place.get("primaryType"):
        types.add(place["primaryType"])
    return bool(types & FOOD_TYPES)


def is_chain(name: str) -> bool:
    n = name.lower()
    return any(kw.lower() in n for kw in CHAIN_KEYWORDS)


def normalize(place: dict) -> dict | None:
    pid = place.get("id")
    dn = place.get("displayName") or {}
    name = dn.get("text") if isinstance(dn, dict) else None
    address = place.get("formattedAddress", "")
    loc = place.get("location") or {}
    lat = loc.get("latitude")
    lng = loc.get("longitude")
    ptype = place.get("primaryType") or ((place.get("types") or [None])[0] if place.get("types") else None)

    if not (pid and name and lat is not None and lng is not None):
        return None

    # 先頭写真の resource name を photo_reference に
    photos = place.get("photos") or []
    photo_ref = ""
    if photos and isinstance(photos, list):
        first = photos[0]
        if isinstance(first, dict):
            photo_ref = first.get("name", "") or ""

    return {
        "place_id": pid,
        "name": name,
        "address": address,
        "lat": lat,
        "lng": lng,
        "type": ptype or "",
        "photo_reference": photo_ref,
    }


def main() -> None:
    api_key = load_key()

    print("=" * 50)
    print("BOKUMO get_shops.py")
    print("=" * 50)

    all_places: list[dict] = []
    for area in AREAS:
        print(f"\n[fetch] {area['name']} (lat={area['lat']}, lng={area['lng']}, r={area['radius']}m)")
        places = fetch_area(api_key, area)
        print(f"   → 取得: {len(places)} 件")
        all_places.extend(places)

    print()
    print(f"合計取得: {len(all_places)} 件")

    seen: set[str] = set()
    shops: list[dict] = []
    skipped_dup = 0
    skipped_nonfood = 0
    skipped_chain = 0
    skipped_invalid = 0

    for p in all_places:
        row = normalize(p)
        if not row:
            skipped_invalid += 1
            continue
        if row["place_id"] in seen:
            skipped_dup += 1
            continue
        if not is_food(p):
            skipped_nonfood += 1
            continue
        if is_chain(row["name"]):
            skipped_chain += 1
            continue
        seen.add(row["place_id"])
        shops.append(row)

    out_path = Path(__file__).resolve().parent / "shops_raw.json"
    out_path.write_text(
        json.dumps(shops, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 50)
    print("処理結果")
    print("=" * 50)
    print(f"  採用       : {len(shops)} 件")
    print(f"  除外 重複  : {skipped_dup} 件")
    print(f"  除外 非飲食: {skipped_nonfood} 件")
    print(f"  除外 チェーン: {skipped_chain} 件")
    print(f"  除外 不正  : {skipped_invalid} 件")
    print()
    print(f"出力: {out_path}")


if __name__ == "__main__":
    main()
