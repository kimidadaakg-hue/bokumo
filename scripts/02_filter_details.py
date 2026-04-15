"""
raw_central.json を重複除去＋チェーン除外＋飲食typeフィルタし、
Place Details で各店の公式情報を取得する。

出力: scripts/details_central.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR / "raw_central.json"
OUT_PATH = SCRIPT_DIR / "details_central.json"

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

FOOD_TYPES = {
    "restaurant", "cafe", "bakery", "bar", "meal_takeaway", "meal_delivery",
    "food", "japanese_restaurant", "italian_restaurant", "french_restaurant",
    "chinese_restaurant", "korean_restaurant", "american_restaurant",
    "seafood_restaurant", "sushi_restaurant", "ramen_restaurant", "steak_house",
    "pizza_restaurant", "hamburger_restaurant", "sandwich_shop", "coffee_shop",
    "dessert_shop", "dessert_restaurant", "ice_cream_shop", "brunch_restaurant",
    "breakfast_restaurant", "thai_restaurant", "indian_restaurant", "mexican_restaurant",
    "vegetarian_restaurant", "vegan_restaurant", "asian_restaurant",
    "mediterranean_restaurant", "spanish_restaurant", "greek_restaurant",
    "japanese_izakaya_restaurant", "yakitori_restaurant", "yakiniku_restaurant",
    "udon_noodle_shop", "soba_noodle_shop", "cake_shop", "pastry_shop",
    "fine_dining_restaurant", "western_restaurant", "family_restaurant",
    "food_store", "tea_house", "juice_shop",
}

CHAIN_KEYWORDS = [
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
    "mcdonald", "マクドナルド",
    "kfc", "ケンタッキー",
    "burger king", "バーガーキング",
    "mos burger", "モスバーガー",
    "lotteria", "ロッテリア",
    "freshness", "フレッシュネス",
    "subway", "サブウェイ",
    "first kitchen", "ファーストキッチン",
    "yoshinoya", "吉野家",
    "sukiya", "すき家",
    "matsuya", "松屋",
    "nakau", "なか卯",
    "ootoya", "大戸屋",
    "yayoiken", "やよい軒",
    "ichiran", "一蘭",
    "ippudo", "一風堂",
    "tenkaippin", "天下一品",
    "kourakuen", "幸楽苑",
    "hidakaya", "日高屋",
    "watami", "ワタミ", "和民",
    "shirokiya", "白木屋",
    "kinnokura", "金の蔵",
    "torikizoku", "鳥貴族",
    "isomaru", "磯丸",
    "gusto", "ガスト",
    "saizeriya", "サイゼリヤ",
    "denny", "デニーズ",
    "jonathan", "ジョナサン",
    "bamiyan", "バーミヤン",
    "royal host", "ロイヤルホスト",
    "coco's", "ココス",
    "sushiro", "スシロー",
    "kura sushi", "くら寿司",
    "kappa", "かっぱ寿司",
    "hamazushi", "はま寿司",
    "ganko", "がんこ",
    "cocoichi", "ココイチ", "co壱番屋",
    "marugame", "丸亀製麺",
    "hanamaru", "はなまるうどん",
    "ringer hut", "リンガーハット",
    "pepper lunch", "ペッパーランチ",
    "mister donut", "ミスタードーナツ", "ミスド",
    "krispy kreme", "クリスピー",
    "baskin", "サーティワン",
    # 北海道ローカルチェーン
    "六花亭",
    "白い恋人",
    "石屋製菓",
    "きのとや",
    "もりもと",
    "ロイズ", "royce",
    "北菓楼",
    "山頭火",
    "すみれ",
    "純連",
    "けやき",
    "そらち",
    "串鳥",
    "とんでん",
    "かつや",
    "はなまさ",
    "ベビーフェイス",
    "モンシェール",
    "鎌倉パスタ",
    "ひらまつ",
    "ワイアードカフェ",
    "タリーズ",
    "プロント",
]


def is_food(place: dict) -> bool:
    types = set(place.get("types", []) or [])
    if place.get("primaryType"):
        types.add(place["primaryType"])
    return bool(types & FOOD_TYPES)


def is_chain(name: str) -> bool:
    n = name.lower()
    return any(kw.lower() in n for kw in CHAIN_KEYWORDS)


def fetch_detail(api_key: str, place_id: str) -> dict | None:
    url = f"https://places.googleapis.com/v1/places/{place_id}?languageCode=ja&regionCode=JP"
    req = request.Request(
        url, method="GET",
        headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELD_MASK},
    )
    try:
        with request.urlopen(req, timeout=20) as res:
            return json.loads(res.read().decode("utf-8"))
    except error.HTTPError as e:
        print(f"   [API {e.code}]", file=sys.stderr)
        return None
    except Exception as e:
        print(f"   [err] {e}", file=sys.stderr)
        return None


def main() -> None:
    key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if not key:
        print("ERROR: GOOGLE_PLACES_API_KEY 未設定", file=sys.stderr)
        sys.exit(1)

    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    print(f"入力: {len(raw)} 件")

    # Step 1: dedupe
    seen: set[str] = set()
    unique: list[dict] = []
    for r in raw:
        pid = r.get("id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        unique.append(r)
    print(f"重複除去後: {len(unique)} 件")

    # Step 2: filter
    candidates: list[dict] = []
    dropped_chain = 0
    dropped_food = 0
    for r in unique:
        name = (r.get("displayName") or {}).get("text", "")
        if not name:
            continue
        if not is_food(r):
            dropped_food += 1
            continue
        if is_chain(name):
            dropped_chain += 1
            continue
        candidates.append(r)
    print(f"チェーン除外: {dropped_chain} / 非飲食除外: {dropped_food}")
    print(f"候補: {len(candidates)} 件")
    print()

    # Step 3: Place Details 取得
    details: list[dict] = []
    closed = 0
    errors = 0

    for i, c in enumerate(candidates, 1):
        name = (c.get("displayName") or {}).get("text", "")
        pid = c.get("id")
        print(f"[{i}/{len(candidates)}] {name}")
        d = fetch_detail(key, pid)
        time.sleep(0.25)
        if not d:
            errors += 1
            continue
        status = d.get("businessStatus", "")
        if status and status != "OPERATIONAL":
            print(f"   → SKIP ({status})")
            closed += 1
            continue
        # canonical shape
        loc = d.get("location") or {}
        details.append({
            "place_id": d.get("id"),
            "name": (d.get("displayName") or {}).get("text", name),
            "address": d.get("formattedAddress", ""),
            "lat": loc.get("latitude"),
            "lng": loc.get("longitude"),
            "primaryType": d.get("primaryType", ""),
            "types": d.get("types", []),
            "googleMapsUri": d.get("googleMapsUri", ""),
            "websiteUri": d.get("websiteUri", ""),
            "_fetched_at": c.get("_fetched_at", ""),
        })

    OUT_PATH.write_text(
        json.dumps(details, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"=== 完了 ===")
    print(f"営業中採用: {len(details)} 件")
    print(f"閉店スキップ: {closed} 件")
    print(f"エラー: {errors} 件")
    print(f"出力: {OUT_PATH}")


if __name__ == "__main__":
    main()
