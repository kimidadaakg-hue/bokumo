"""
analyzed_central.json から 緩和された kids-only フィルタを適用し、
BOKUMO 本体用 data/shops.json を出力する。

緩和プランC:
  - score >= 4 なら無条件で採用 (Gemini の総合判定を信頼)
  - score >= 3 で evidence に「子連れ/家族」関連キーワードがあれば採用
  - チェーン店・非飲食店(映画館/ホテル)は除外
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent

IN_PATH = SCRIPT_DIR / "analyzed_central.json"
OUT_PATH = ROOT / "data" / "shops.json"
REMOVED_PATH = ROOT / "data" / "shops_removed.json"

# プランC: 子連れ直接言及 + 家族
POSITIVE_KEYWORDS = [
    "子連れ", "子ども", "子供", "こども", "赤ちゃん",
    "離乳食", "ミルク", "ベビー", "キッズ", "子育て",
    "親子", "幼児", "ハイチェア", "キッズチェア",
    "お子様", "お子さん", "家族連れ", "家族",
]

NEGATIVE_PATTERNS = [
    r"入店.{0,5}(不可|出来ません|できません|お断り|禁止)",
    r"(子供|こども|小学生|未就学児|幼児).{0,10}(不可|出来ません|できません|お断り|禁止|NG)",
    r"未満.{0,5}(不可|出来ません|できません|入れません)",
]

# 明らかに飲食店ではない type (誤混入対策)
NON_FOOD_TYPES = {
    "movie_theater", "lodging", "hotel", "resort_hotel",
    "extended_stay_hotel", "bed_and_breakfast",
    "tourist_attraction", "convenience_store",
    "supermarket", "grocery_store", "shopping_mall",
    "department_store", "store",
}

# 追加チェーン除外リスト (既存のチェーン除外を擦り抜けたもの)
EXTRA_CHAIN_KEYWORDS = [
    "びっくりドンキー",
    "ヴィクトリアステーション",
    "回転寿しトリトン",
    "回転寿司根室花まる", "根室花まる", "根室 花まる",
    "暖龍",
    "SAMA", "sama",
    "かつ徳",
    "六花亭",
    "つぼ八",
    "はま寿司",
    "スシロー",
    "くら寿司",
    "かっぱ寿司",
    "ラーメン山頭火", "山頭火",
    "白樺山荘",
    "味の時計台",
    "どさん子",
    "南部亭",
    "串鳥",
    "とんでん",
    "ミスタードーナツ",
    "サーティワン",
    "クリスピー",
]

GENRE_MAP = {
    "cafe": "カフェ", "coffee_shop": "カフェ",
    "tea_house": "カフェ", "dessert_shop": "カフェ",
    "dessert_restaurant": "カフェ", "cake_shop": "カフェ",
    "pastry_shop": "カフェ", "ice_cream_shop": "カフェ",
    "bakery": "カフェ", "juice_shop": "カフェ",
    "japanese_restaurant": "和食", "sushi_restaurant": "和食",
    "ramen_restaurant": "和食", "udon_noodle_shop": "和食",
    "soba_noodle_shop": "和食", "japanese_izakaya_restaurant": "和食",
    "yakitori_restaurant": "和食", "yakiniku_restaurant": "和食",
    "italian_restaurant": "イタリアン", "pizza_restaurant": "イタリアン",
    "french_restaurant": "洋食", "western_restaurant": "洋食",
    "american_restaurant": "洋食", "steak_house": "洋食",
    "hamburger_restaurant": "洋食", "sandwich_shop": "洋食",
    "mediterranean_restaurant": "洋食", "spanish_restaurant": "洋食",
    "greek_restaurant": "洋食",
    "chinese_restaurant": "その他", "korean_restaurant": "その他",
    "thai_restaurant": "その他", "indian_restaurant": "その他",
    "mexican_restaurant": "その他", "asian_restaurant": "その他",
    "seafood_restaurant": "和食",
    "vegetarian_restaurant": "その他", "vegan_restaurant": "その他",
    "family_restaurant": "その他", "food_store": "その他",
    "fine_dining_restaurant": "洋食",
    "bar": "その他", "restaurant": "その他",
}

DEFAULT_IMAGES = {
    "カフェ":    "https://images.unsplash.com/photo-1445116572660-236099ec97a0?w=800",
    "和食":      "https://images.unsplash.com/photo-1514326640560-7d063ef2aed5?w=800",
    "洋食":      "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
    "イタリアン": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=800",
    "その他":    "https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=800",
}


def has_positive_evidence(evs: list[str]) -> tuple[bool, list[str]]:
    matched = []
    for ev in evs:
        if not isinstance(ev, str):
            continue
        if any(re.search(p, ev) for p in NEGATIVE_PATTERNS):
            continue
        if any(kw in ev for kw in POSITIVE_KEYWORDS):
            matched.append(ev)
    return (len(matched) > 0, matched)


def is_non_food(d: dict) -> bool:
    ptype = d.get("primaryType", "")
    if ptype in NON_FOOD_TYPES:
        return True
    types = set(d.get("types") or [])
    if types & NON_FOOD_TYPES:
        return True
    # 名前でホテル系判定
    name = d.get("name", "")
    if re.search(r"(ホテル|hotel|シネマ|cinema|プラザ|旅館|公館|百貨店|市場 店舗)", name, re.IGNORECASE):
        return True
    return False


def is_extra_chain(name: str) -> bool:
    n = name.lower()
    for kw in EXTRA_CHAIN_KEYWORDS:
        if kw.lower() in n:
            return True
    return False


def genre_from_type(ptype: str) -> str:
    return GENRE_MAP.get(ptype, "その他")


def area_from_address(address: str) -> str:
    if "宮ケ丘" in address or "宮の森" in address:
        return "宮の森"
    if re.search(r"北[1-3]条", address) or "大通" in address:
        return "大通・駅前"
    if re.search(r"南[4-7]条", address) or "すすきの" in address:
        return "ススキノ"
    if re.search(r"南[89]条|南1[01]条", address) or "中島" in address:
        return "中島公園"
    if re.search(r"南[1-3]条.*西2[3-9]", address) or re.search(r"北[1-3]条.*西2[3-9]", address):
        return "円山"
    if "伏見" in address:
        return "伏見"
    if "山鼻" in address:
        return "山鼻"
    return "中央区"


def main() -> None:
    data = json.loads(IN_PATH.read_text(encoding="utf-8"))
    print(f"入力: {len(data)} 件")

    kept = []
    removed = []

    for d in data:
        name = d.get("name", "")
        score = d.get("score", 3)
        evs = d.get("evidence") or []

        # 非飲食店除外
        if is_non_food(d):
            removed.append({**d, "_reason": "非飲食(ホテル/映画館等)"})
            continue

        # 追加チェーン除外
        if is_extra_chain(name):
            removed.append({**d, "_reason": "チェーン店"})
            continue

        # score <= 2 は問答無用で除外
        if score <= 2:
            removed.append({**d, "_reason": f"score={score}(子連れ不向き)"})
            continue

        # score >= 4 なら無条件採用 (Gemini の総合判定を信頼)
        if score >= 4:
            kept.append(d)
            continue

        # score == 3 は evidence に子連れ/家族 キーワード必要
        ok, _ = has_positive_evidence(evs)
        if ok:
            kept.append(d)
        else:
            removed.append({**d, "_reason": "score=3 でevidence無し"})

    # shape → BOKUMO 形式
    shops = []
    for i, d in enumerate(kept, 1):
        genre = genre_from_type(d.get("primaryType", ""))
        area = area_from_address(d.get("address", ""))
        shops.append({
            "id": i,
            "place_id": d["place_id"],
            "name": d["name"],
            "area": area,
            "genre": genre,
            "tags": d.get("tags", []),
            "description": d.get("description", ""),
            "score": d.get("score", 3),
            "lat": d["lat"],
            "lng": d["lng"],
            "tabelog_url": d.get("googleMapsUri", ""),
            "image_url": DEFAULT_IMAGES.get(genre, DEFAULT_IMAGES["その他"]),
            "is_chain": False,
            "website_uri": d.get("websiteUri", ""),
            "evidence": d.get("evidence", []),
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(shops, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REMOVED_PATH.write_text(
        json.dumps(removed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"採用: {len(shops)} 件")
    print(f"除外: {len(removed)} 件")
    print()
    for s in shops:
        tag_str = "/".join(s["tags"]) if s["tags"] else "タグなし"
        print(f"  [★{s['score']}] {s['area']:8} {s['genre']:6} {s['name'][:25]:25} [{tag_str}]")
    print()
    print(f"出力: {OUT_PATH}")


if __name__ == "__main__":
    main()
