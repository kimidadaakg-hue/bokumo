"""
data/shops.json をクリーンアップする。

- ダミー(place_idなし)を除外
- 西区琴似/二十四軒 を除外
- チェーン店を除外
- 子連れに不向きな高級店を除外
- テイクアウト専門を除外
- image_url を genre ごとのデフォルトで埋める
- genre の誤りを軽微補正(ラーメンを和食に)
- id を振り直し
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOPS_PATH = ROOT / "data" / "shops.json"

# 除外する place_id
EXCLUDE_IDS = {
    # 西区 (エリア外)
    "ChIJVVW8yQ0pC18RTR7zffGlJSQ",  # 廣瀬商店
    "ChIJZ0nbSCYpC18RJJ--OnKUAx8",  # にく式 琴似店
    "ChIJAatfsBkpC18RUVy8cpO5S-k",  # トナリハジンジャ
    "ChIJfV8lqrIpC18RUjOPCdBFkXI",  # 大船鮨
    "ChIJOU74lLcpC18RTxESP-7unhw",  # 山頭火 宮の森店 (住所は西区二十四軒)
    # チェーン店
    "ChIJc9WzuekpC18RGnGeYUCLfgM",  # 六花亭 円山店
    "ChIJp2QySN0pC18R7poKmLT4-TU",  # 六花亭 神宮茶屋店
    "ChIJK8KcCewpC18R3uoLT3rEEJw",  # パティスリーモンシェール
    "ChIJab64zMYpC18RvCF3UY2zjfI",  # ベビーフェイスプラネッツ
    "ChIJLQEo_7UpC18Rm-cTHVkuO4A",  # とんでん 宮の森店
    # 高級店 (子連れ非推奨)
    "ChIJ14UhkcMpC18RYEwgnUQ8T10",  # モリエール
    "ChIJ3cVpe8IpC18R9_v6oY2YRh8",  # オーベルジュ・ド・リル
    "ChIJH6QIh8EpC18R_BXy4M2xzWE",  # すし善 本店
    "ChIJ___DCsApC18RPJotcFOf7Ws",  # Sushi yashiro
    # テイクアウト専門
    "ChIJ7dvGLoUpC18RlHUkIeII7Zs",  # 円山牛乳販売店
    "ChIJf2GHJBEpC18RKKGoFJtzoeA",  # KIYOHACHI
}

# genre 別のデフォルト画像 (Unsplash)
DEFAULT_IMAGES = {
    "カフェ":    "https://images.unsplash.com/photo-1445116572660-236099ec97a0?w=800",
    "和食":      "https://images.unsplash.com/photo-1514326640560-7d063ef2aed5?w=800",
    "洋食":      "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
    "イタリアン": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=800",
    "その他":    "https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=800",
}


def fix_genre(shop: dict) -> str:
    """明らかな誤分類を軽く補正."""
    g = shop.get("genre", "その他")
    name = shop.get("name", "")
    if "そば" in name or "ラーメン" in name or "らーめん" in name:
        return "和食"
    return g


def fix_area(shop: dict) -> str:
    """座標で円山/宮の森を判定(北緯が高いものは宮の森寄り)."""
    name = shop.get("name", "")
    if "神宮" in name or "宮ケ丘" in name:
        return "宮の森"
    return shop.get("area", "円山")


def main() -> None:
    data = json.loads(SHOPS_PATH.read_text(encoding="utf-8"))
    print(f"入力: {len(data)} 件")

    kept: list[dict] = []
    removed_dummy = 0
    removed_exclude = 0

    for s in data:
        pid = s.get("place_id")
        # ダミー除外
        if not pid:
            removed_dummy += 1
            continue
        if pid in EXCLUDE_IDS:
            removed_exclude += 1
            continue
        kept.append(s)

    # 整形 & ID 振り直し
    cleaned: list[dict] = []
    for i, s in enumerate(kept, 1):
        genre = fix_genre(s)
        area = fix_area(s)
        image = s.get("image_url") or DEFAULT_IMAGES.get(genre, DEFAULT_IMAGES["その他"])
        cleaned.append({
            "id": i,
            "place_id": s.get("place_id"),
            "name": s["name"],
            "area": area,
            "genre": genre,
            "tags": s.get("tags", []),
            "description": s.get("description", ""),
            "score": s.get("score", 3),
            "lat": s["lat"],
            "lng": s["lng"],
            "tabelog_url": s.get("tabelog_url", ""),
            "image_url": image,
            "is_chain": False,
        })

    SHOPS_PATH.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"除外: ダミー={removed_dummy} / 手動除外={removed_exclude}")
    print(f"採用: {len(cleaned)} 件")
    print()
    for s in cleaned:
        tag_str = "/".join(s["tags"]) if s["tags"] else "タグなし"
        print(f"  {s['id']:2}. [★{s['score']}] {s['area']} {s['genre']:6} {s['name']:25} [{tag_str}]")


if __name__ == "__main__":
    main()
