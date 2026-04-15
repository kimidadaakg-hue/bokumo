#!/usr/bin/env python3
"""
build_shops.py - Convert kid_friendly.json into BOKUMO's data/shops.json format.

Input:  scripts/pipeline/kid_friendly.json
Output: data/shops.json          (shops for the BOKUMO site)
        data/shops_removed.json  (excluded shops with _reason)
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
INPUT_PATH = BASE_DIR / "kid_friendly_merged.json"
INPUT_FALLBACK = BASE_DIR / "kid_friendly.json"  # merged がなければ fallback
OUTPUT_PATH = PROJECT_ROOT / "data" / "shops.json"
REMOVED_PATH = PROJECT_ROOT / "data" / "shops_removed.json"

# ---------------------------------------------------------------------------
# Hokkaido bounding box
# ---------------------------------------------------------------------------
LAT_MIN, LAT_MAX = 41.3, 45.6
LNG_MIN, LNG_MAX = 139.3, 145.8

# ---------------------------------------------------------------------------
# Hotel / non-restaurant exclusion keywords
# ---------------------------------------------------------------------------
HOTEL_KEYWORDS = [
    "ホテル", "hotel", "旅館", "リゾート", "resort", "inn",
    "グランドホテル", "プリンス", "ドーミーイン",
    # 病院
    "病院", "クリニック", "医院", "歯科", "診療所",
    # カラオケ
    "カラオケ", "ビッグエコー", "まねきねこ", "ジャンカラ",
    "シダックス", "コート・ダジュール", "BanBan",
    # 百貨店
    "大丸", "丸井", "三越", "伊勢丹", "高島屋",
]

# ---------------------------------------------------------------------------
# ネガティブパターン (evidence/description にこのパターンがあれば除外)
# ---------------------------------------------------------------------------
import re as _re
NEGATIVE_PATTERNS = [
    _re.compile(r"お子様.{0,5}(不可|お断り|遠慮|禁止)"),
    _re.compile(r"子連れ.{0,5}(不可|お断り|遠慮|禁止|不向き)"),
    _re.compile(r"小学生.{0,5}(不可|お断り|遠慮|禁止)"),
    _re.compile(r"未満.{0,5}(不可|お断り|入れません)"),
    _re.compile(r"(子供|こども).{0,10}(不可|お断り|禁止|NG)"),
    _re.compile(r"入店.{0,5}(不可|お断り|禁止|出来ません|できません)"),
]

# ---------------------------------------------------------------------------
# Genre mapping
# ---------------------------------------------------------------------------
GENRE_MAP = {
    "cafe": "カフェ",
    "coffee_shop": "カフェ",
    "bakery": "カフェ",
    "tea_house": "カフェ",
    "dessert_restaurant": "カフェ",
    "japanese_restaurant": "和食",
    "sushi_restaurant": "和食",
    "ramen_restaurant": "和食",
    "yakitori_restaurant": "和食",
    "yakiniku_restaurant": "和食",
    "seafood_restaurant": "和食",
    "japanese_izakaya_restaurant": "和食",
    "italian_restaurant": "イタリアン",
    "pizza_restaurant": "イタリアン",
    "french_restaurant": "洋食",
    "steak_house": "洋食",
    "western_restaurant": "洋食",
    "american_restaurant": "洋食",
    "hamburger_restaurant": "洋食",
}

# ---------------------------------------------------------------------------
# Dummy images by genre (Unsplash)
# ---------------------------------------------------------------------------
DUMMY_IMAGES = {
    "カフェ": "https://images.unsplash.com/photo-1445116572660-236099ec97a0?w=800",
    "和食": "https://images.unsplash.com/photo-1514326640560-7d063ef2aed5?w=800",
    "洋食": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
    "イタリアン": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=800",
    "その他": "https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=800",
}


# ---------------------------------------------------------------------------
# Area detection
# ---------------------------------------------------------------------------
def detect_area(address: str) -> str:
    # 札幌市中央区の細分化
    if "中央区" in address and "札幌" in address:
        m = re.search(r"(南|北)(\d+)条", address)
        if m:
            d, n = m.group(1), int(m.group(2))
            if d == "北":
                return "札幌駅周辺"
            if n <= 3:
                return "大通"
            if n <= 7:
                return "すすきの"
            return "中島公園・山鼻"
        if "宮の森" in address:
            return "宮の森"
        if "円山" in address:
            return "円山"
        return "札幌中央区"

    # 札幌市他区
    for ku in [
        "北区", "東区", "白石区", "厚別区", "豊平区",
        "清田区", "南区", "西区", "手稲区",
    ]:
        if ku in address and "札幌" in address:
            # 豊平区の細分化
            if ku == "豊平区":
                if "平岸" in address:
                    return "平岸"
                if "月寒" in address or "美園" in address:
                    return "月寒・美園"
                if "豊平" in address:
                    return "豊平"
            # 北区の細分化
            if ku == "北区":
                if "麻生" in address or "新琴似" in address:
                    return "麻生・新琴似"
                m2 = re.search(r"北(\d+)条", address)
                if m2 and int(m2.group(1)) <= 12:
                    return "札幌北区南部"
                if m2:
                    return "札幌北区北部"
            return f"札幌{ku}"

    if "札幌" in address:
        return "札幌"

    # 旭川の細分化
    if "旭川" in address:
        if "永山" in address:
            return "旭川永山"
        if "神楽" in address or "神居" in address:
            return "旭川神楽"
        m = re.search(r"(\d+)条", address)
        if m and int(m.group(1)) <= 5:
            return "旭川駅周辺"
        if m:
            return "旭川郊外"
        return "旭川"

    # 函館の細分化
    if "函館" in address:
        if any(k in address for k in ["五稜郭", "本町", "梁川"]):
            return "五稜郭"
        if any(k in address for k in ["末広", "豊川", "元町", "大町", "弁天"]):
            return "函館ベイエリア"
        if any(k in address for k in ["松風", "若松", "大門", "大手"]):
            return "函館駅前"
        if any(k in address for k in ["美原", "石川", "桔梗", "昭和"]):
            return "函館郊外"
        return "函館"

    # 小樽の細分化
    if "小樽" in address:
        if any(k in address for k in ["堺町", "色内", "港町"]):
            return "小樽運河・堺町"
        if any(k in address for k in ["稲穂", "花園"]):
            return "小樽駅周辺"
        return "小樽"

    # 他の都市
    cities = [
        "帯広", "釧路", "苫小牧", "千歳", "北見", "室蘭", "富良野", "美瑛",
        "稚内", "網走", "紋別", "名寄", "留萌", "士別", "根室",
        "恵庭", "江別", "石狩", "岩見沢", "北広島", "滝川", "砂川", "深川",
        "伊達", "登別",
    ]
    for c in cities:
        if c in address:
            return c

    return "北海道"


def detect_genre(primary_type: str) -> str:
    return GENRE_MAP.get(primary_type, "その他")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    input_path = INPUT_PATH if INPUT_PATH.exists() else INPUT_FALLBACK
    if not input_path.exists():
        print(f"ERROR: {INPUT_PATH} も {INPUT_FALLBACK} も見つかりません")
        sys.exit(1)

    shops = json.loads(input_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(shops)} shops from {input_path.name}")

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    accepted = []
    removed = []
    seen_place_ids = set()

    reason_counts = Counter()

    for shop in shops:
        place_id = shop.get("place_id", "")
        tags = shop.get("tags", [])
        lat = shop.get("lat", 0)
        lng = shop.get("lng", 0)

        # --- Exclusion checks ---
        # Hotel / non-restaurant
        name = shop.get("name", "")
        if any(kw.lower() in name.lower() for kw in HOTEL_KEYWORDS):
            reason = "hotel"
            reason_counts[reason] += 1
            shop["_reason"] = reason
            removed.append(shop)
            continue

        # Empty tags
        if not tags:
            reason = "empty_tags"
            reason_counts[reason] += 1
            shop["_reason"] = reason
            removed.append(shop)
            continue

        # Negative patterns (お子様連れ不可 等)
        ev_text = " ".join(str(e) for e in shop.get("evidence", []))
        desc = shop.get("description", "")
        combined_text = ev_text + " " + desc
        if any(p.search(combined_text) for p in NEGATIVE_PATTERNS):
            reason = "negative_pattern"
            reason_counts[reason] += 1
            shop["_reason"] = reason
            removed.append(shop)
            continue

        # Smoking shop
        SMOKING_KEYWORDS = ["喫煙可", "喫煙席", "喫煙OK", "タバコ吸える", "たばこ吸える", "灰皿あり"]
        if any(kw in combined_text for kw in SMOKING_KEYWORDS):
            reason = "smoking"
            reason_counts[reason] += 1
            shop["_reason"] = reason
            removed.append(shop)
            continue

        # Score 2 or below
        if shop.get("score", 3) <= 2:
            reason = "low_score"
            reason_counts[reason] += 1
            shop["_reason"] = reason
            removed.append(shop)
            continue

        # Out of Hokkaido bbox
        if not (LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX):
            reason = "outside_hokkaido"
            reason_counts[reason] += 1
            shop["_reason"] = reason
            removed.append(shop)
            continue

        # Duplicate place_id
        if place_id in seen_place_ids:
            reason = "duplicate_place_id"
            reason_counts[reason] += 1
            shop["_reason"] = reason
            removed.append(shop)
            continue

        seen_place_ids.add(place_id)
        accepted.append(shop)

    # --- Build final format ---
    output = []
    for idx, shop in enumerate(accepted, start=1):
        address = shop.get("address", "")
        primary_type = shop.get("primaryType", "")
        genre = detect_genre(primary_type)
        image_url = shop.get("image_url", "")

        # Default image if empty
        if not image_url:
            image_url = DUMMY_IMAGES.get(genre, DUMMY_IMAGES["その他"])

        entry = {
            "id": idx,
            "place_id": shop.get("place_id", ""),
            "name": shop.get("name", ""),
            "area": detect_area(address),
            "genre": genre,
            "tags": shop.get("tags", []),
            "description": "",
            "score": shop.get("score", 3),
            "lat": shop.get("lat", 0),
            "lng": shop.get("lng", 0),
            "tabelog_url": shop.get("googleMapsUri", ""),
            "image_url": image_url,
            "is_chain": False,
            "evidence": shop.get("evidence", []),
            "source": shop.get("source", ""),
        }
        output.append(entry)

    # --- Write outputs ---
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    REMOVED_PATH.write_text(
        json.dumps(removed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- Report ---
    print()
    print("=" * 60)
    print("  BUILD REPORT")
    print("=" * 60)

    print(f"\n  Input:    {len(shops)}")
    print(f"  Output:   {len(output)}")
    print(f"  Excluded: {len(removed)}")
    if reason_counts:
        for reason, count in reason_counts.most_common():
            print(f"    - {reason}: {count}")

    # Area distribution (top 20)
    area_counter = Counter(s["area"] for s in output)
    print(f"\n--- Area Distribution (top 20) ---")
    for area, count in area_counter.most_common(20):
        bar = "#" * min(count, 50)
        print(f"  {area:<16s} {count:>4d}  {bar}")

    # Genre distribution
    genre_counter = Counter(s["genre"] for s in output)
    print(f"\n--- Genre Distribution ---")
    for genre, count in genre_counter.most_common():
        bar = "#" * min(count, 50)
        print(f"  {genre:<12s} {count:>4d}  {bar}")

    # Score distribution with star bar chart
    score_counter = Counter(s["score"] for s in output)
    print(f"\n--- Score Distribution ---")
    for score in sorted(score_counter.keys()):
        count = score_counter[score]
        stars = "\u2605" * score + "\u2606" * (5 - score)
        bar = "#" * min(count, 50)
        print(f"  {stars}  ({score})  {count:>4d}  {bar}")

    # Tag distribution
    tag_counter = Counter()
    for s in output:
        for t in s["tags"]:
            tag_counter[t] += 1
    print(f"\n--- Tag Distribution ---")
    for tag, count in tag_counter.most_common():
        bar = "#" * min(count, 50)
        print(f"  {tag:<20s} {count:>4d}  {bar}")

    # Source distribution
    source_counter = Counter(s["source"] for s in output)
    print(f"\n--- Source Distribution ---")
    for source, count in source_counter.most_common():
        bar = "#" * min(count, 50)
        print(f"  {source:<12s} {count:>4d}  {bar}")

    # Default image usage
    default_img_count = sum(
        1 for s in output if s["image_url"] in DUMMY_IMAGES.values()
    )
    print(f"\n  Shops with default image: {default_img_count}/{len(output)}")

    print()
    print(f"  Written: {OUTPUT_PATH}")
    print(f"  Written: {REMOVED_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
