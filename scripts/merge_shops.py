"""
shops_raw.json (Places API 取得結果) を
BOKUMO 本体の data/shops.json 形式に変換する。

フィルタ:
  - 中央区のみ (西区琴似/二十四軒を除外)
  - テイクアウト/デリバリー専門を除外
  - 北海道ローカルチェーンを除外
  - 子連れに不向きな超高級店を除外

スコア・タグ:
  - ジャンル(primaryType)と店名/住所から推測した下書き
  - 実際の子連れ対応状況は Places API では分からないため、
    最終的には人間が調整する前提
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = Path(__file__).resolve().parent / "shops_raw.json"
OUT_PATH = ROOT / "data" / "shops.json"
BACKUP_PATH = ROOT / "data" / "shops.dummy.json"

# 手動で除外する店 (place_id)
# 超高級店 / テイクアウト専門 / ローカルチェーン
EXCLUDE_IDS: set[str] = {
    # 超高級(子連れ非推奨)
    "ChIJ14UhkcMpC18RYEwgnUQ8T10",  # モリエール
    "ChIJ3cVpe8IpC18R9_v6oY2YRh8",  # オーベルジュ・ド・リル サッポロ
    "ChIJH6QIh8EpC18R_BXy4M2xzWE",  # すし善 本店
    "ChIJ___DCsApC18RPJotcFOf7Ws",  # Sushi yashiro
    # テイクアウト専門
    "ChIJ7dvGLoUpC18RlHUkIeII7Zs",  # 円山牛乳販売店
    "ChIJf2GHJBEpC18RKKGoFJtzoeA",  # KIYOHACHICHOPPEDSALAD
    # 北海道ローカル/関西チェーン
    "ChIJc9WzuekpC18RGnGeYUCLfgM",  # 六花亭 円山店
    "ChIJp2QySN0pC18R7poKmLT4-TU",  # 六花亭 神宮茶屋店
    "ChIJK8KcCewpC18R3uoLT3rEEJw",  # パティスリーモンシェール
    "ChIJLQEo_7UpC18Rm-cTHVkuO4A",  # とんでん
    "ChIJab64zMYpC18RvCF3UY2zjfI",  # ベビーフェイスプラネッツ
}

# エリア判定: 住所で中央区チェック
def is_in_target_area(address: str) -> bool:
    if "中央区" not in address:
        return False
    return True


def detect_area(address: str, lat: float) -> str:
    """円山 / 宮の森 を判定."""
    if "宮ケ丘" in address or "宮の森" in address:
        return "宮の森"
    return "円山"


# ジャンル判定: primaryType → 日本語ジャンル
def detect_genre(ptype: str, name: str) -> str:
    p = ptype.lower()
    n = name.lower()
    if "cafe" in p or "coffee" in p or "茶寮" in name or "茶屋" in name:
        return "カフェ"
    if "bakery" in p or "bread" in p or name.endswith("麦") or "パン" in name:
        return "カフェ"
    if "italian" in p or "pizza" in p:
        return "イタリアン"
    if "french" in p or "western" in p or "steak" in p:
        return "洋食"
    if "japanese" in p or "sushi" in p or "ramen" in p or "そば" in name or "蕎麦" in name:
        return "和食"
    return "その他"


# スコア & タグ推測ロジック
def guess_score_and_tags(shop: dict[str, Any]) -> tuple[int, list[str]]:
    ptype = (shop.get("type") or "").lower()
    name = shop.get("name") or ""

    # デフォルト
    score = 3
    tags: list[str] = []

    if "cafe" in ptype or "茶寮" in name or "茶屋" in name:
        score = 4
        tags = ["ベビーカーOK", "キッズチェアあり"]
    elif "bakery" in ptype or name.endswith("麦"):
        score = 4
        tags = ["ベビーカーOK", "キッズチェアあり"]
    elif "italian" in ptype:
        score = 3
        tags = ["キッズチェアあり", "子供メニューあり"]
    elif "ramen" in ptype or "そば" in name:
        score = 3
        tags = ["キッズチェアあり"]
    elif "steak" in ptype:
        score = 3
        tags = ["個室あり", "キッズチェアあり"]
    elif "sushi" in ptype:
        score = 3
        tags = ["座敷あり", "子供メニューあり"]
    elif "japanese" in ptype or "和食" in name:
        score = 4
        tags = ["座敷あり", "子供メニューあり"]
    else:
        tags = ["キッズチェアあり"]

    # 名前ベースの微調整
    if "茶屋" in name:
        tags = list(dict.fromkeys(tags + ["座敷あり"]))

    return score, tags[:3]


# Unsplash のダミー画像プール(ジャンル別)
DEFAULT_IMAGES = {
    "カフェ": "https://images.unsplash.com/photo-1445116572660-236099ec97a0?w=800",
    "和食":   "https://images.unsplash.com/photo-1514326640560-7d063ef2aed5?w=800",
    "洋食":   "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
    "イタリアン": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=800",
    "その他": "https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=800",
}


def main() -> None:
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    print(f"入力: {len(raw)} 件")

    # 既存 data/shops.json をバックアップ (初回のみ)
    if OUT_PATH.exists() and not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(OUT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"既存の {OUT_PATH.name} を {BACKUP_PATH.name} にバックアップ")

    shops: list[dict[str, Any]] = []
    excluded: list[tuple[str, str]] = []

    next_id = 1
    for r in raw:
        pid = r.get("place_id", "")
        name = r.get("name", "")
        address = r.get("address", "")
        lat = r.get("lat")
        lng = r.get("lng")
        ptype = r.get("type", "")

        if pid in EXCLUDE_IDS:
            excluded.append((name, "手動除外(高級店/チェーン/テイクアウト)"))
            continue

        if not is_in_target_area(address):
            excluded.append((name, "エリア外"))
            continue

        area = detect_area(address, lat or 0)
        genre = detect_genre(ptype, name)
        score, tags = guess_score_and_tags(r)

        shops.append({
            "id": next_id,
            "name": name,
            "area": area,
            "genre": genre,
            "tags": tags,
            "description": f"{area}エリアの{genre}のお店。{address.split(' ')[0] if ' ' in address else address}",
            "score": score,
            "lat": lat,
            "lng": lng,
            "tabelog_url": f"https://tabelog.com/hokkaido/A0101/A010102/rstLst/?vs=1&sa=%E5%86%86%E5%B1%B1&sk={name}",
            "image_url": DEFAULT_IMAGES.get(genre, DEFAULT_IMAGES["その他"]),
            "is_chain": False,
        })
        next_id += 1

    OUT_PATH.write_text(
        json.dumps(shops, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"出力: {OUT_PATH}")
    print(f"  採用: {len(shops)} 件")
    print(f"  除外: {len(excluded)} 件")
    print()
    print("--- 採用店舗 ---")
    for s in shops:
        tag_str = " / ".join(s["tags"])
        print(f"  {s['id']:2}. [★{s['score']}] {s['area']} {s['genre']:8} {s['name']:30} [{tag_str}]")
    print()
    print("--- 除外店舗 ---")
    for name, reason in excluded:
        print(f"  - {name}  ({reason})")


if __name__ == "__main__":
    main()
