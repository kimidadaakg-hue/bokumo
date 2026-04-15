"""
data/shops.json のデータ確認・正規化・最終反映を行う。

使い方:
    python3 scripts/apply_shops.py

チェック・除外項目:
  - is_chain == true       → 除外
  - tags が空              → 除外
  - score 未設定           → デフォルト 3
  - 札幌市範囲外(lat 43.0-43.1, lng 141.2-141.4) → 除外
  - 重複 id                → 除外 (後勝ち)
  - image_url 空           → ダミー画像URLを設定

完了後レポート:
  - 登録/除外 店舗数(理由別)
  - タグ別件数
  - スコア別分布
  - Place Photos 月次使用回数
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SHOPS_PATH = ROOT / "data" / "shops.json"
REMOVED_PATH = ROOT / "data" / "shops_removed.json"
PHOTOS_USAGE_PATH = Path(__file__).resolve().parent / "photos_usage.json"

# 札幌市 bbox
LAT_MIN, LAT_MAX = 43.0, 43.1
LNG_MIN, LNG_MAX = 141.2, 141.4

# evidence からタグを自動推論するルール
# (キーワードリスト, 付与するタグ)
TAG_INFERENCE_RULES: list[tuple[list[str], str]] = [
    (["離乳食", "ミルク", "哺乳瓶", "授乳", "ベビーカー", "ストローラー"], "ベビーカーOK"),
    (["離乳食", "お子様メニュー", "キッズメニュー", "お子さまメニュー",
      "子供メニュー", "子ども用", "子供用", "ちびラーメン", "お子様ラーメン",
      "キッズプレート", "お子様ランチ"], "子供メニューあり"),
    (["座敷", "小上がり", "掘りごたつ", "お座敷", "畳"], "座敷あり"),
    (["個室", "半個室", "貸切"], "個室あり"),
    (["キッズチェア", "子供椅子", "こども椅子", "子供用椅子",
      "ハイチェア", "ベビーチェア"], "キッズチェアあり"),
    (["子連れ歓迎", "家族連れ", "お子様連れ", "子ども連れ",
      "子連れでもOK", "子連れOK", "子連れでもいけ",
      "家族", "子供", "子ども", "赤ちゃん", "幼児", "親子"], "騒いでもOK"),
]


def infer_tags_from_evidence(evidence: list[Any]) -> list[str]:
    """evidenceのテキストから該当するタグを推論."""
    if not evidence:
        return []
    joined = " ".join(str(e) for e in evidence if e)
    if not joined:
        return []
    inferred: list[str] = []
    for keywords, tag in TAG_INFERENCE_RULES:
        if tag in inferred:
            continue
        if any(kw in joined for kw in keywords):
            inferred.append(tag)
    return inferred


# ダミー画像 (genre 別)
DUMMY_IMAGES = {
    "カフェ":    "https://images.unsplash.com/photo-1445116572660-236099ec97a0?w=800",
    "和食":      "https://images.unsplash.com/photo-1514326640560-7d063ef2aed5?w=800",
    "洋食":      "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
    "イタリアン": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=800",
    "その他":    "https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=800",
}


def in_sapporo(lat, lng) -> bool:
    try:
        return LAT_MIN <= float(lat) <= LAT_MAX and LNG_MIN <= float(lng) <= LNG_MAX
    except Exception:
        return False


def load_photos_usage() -> dict:
    if not PHOTOS_USAGE_PATH.exists():
        return {"month": "(未記録)", "count": 0}
    try:
        return json.loads(PHOTOS_USAGE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"month": "(読み取り失敗)", "count": 0}


def main() -> None:
    if not SHOPS_PATH.exists():
        print(f"ERROR: {SHOPS_PATH} が見つかりません。")
        return

    data = json.loads(SHOPS_PATH.read_text(encoding="utf-8"))
    print("=" * 50)
    print("BOKUMO apply_shops.py")
    print("=" * 50)
    print(f"入力: {len(data)} 件")
    print()

    kept: list[dict] = []
    removed: list[dict] = []
    reason_counts: dict[str, int] = defaultdict(int)
    seen_ids: set[int] = set()
    inferred_count = 0

    def drop(shop: dict, reason: str) -> None:
        removed.append({**shop, "_reason": reason})
        reason_counts[reason] += 1

    for shop in data:
        # is_chain
        if shop.get("is_chain") is True:
            drop(shop, "is_chain")
            continue

        # tags (空なら evidence から推論してから判定)
        tags = shop.get("tags") or []
        if not isinstance(tags, list):
            tags = []
        if len(tags) == 0:
            inferred = infer_tags_from_evidence(shop.get("evidence") or [])
            if inferred:
                shop["tags"] = inferred
                tags = inferred
                inferred_count += 1
                print(f"  🔧 tag推論 [{shop.get('name','?')}]: {'/'.join(inferred)}")
        if len(tags) == 0:
            drop(shop, "tags_empty")
            continue

        # score 未設定 → 3
        if "score" not in shop or shop.get("score") is None:
            shop["score"] = 3

        # 札幌市範囲
        if not in_sapporo(shop.get("lat"), shop.get("lng")):
            drop(shop, "out_of_sapporo")
            continue

        # 重複 id
        sid = shop.get("id")
        if sid in seen_ids:
            drop(shop, "duplicate_id")
            continue
        if sid is not None:
            seen_ids.add(sid)

        # image_url 空 → ダミー
        if not shop.get("image_url"):
            g = shop.get("genre", "その他")
            shop["image_url"] = DUMMY_IMAGES.get(g, DUMMY_IMAGES["その他"])

        kept.append(shop)

    # id 振り直し (連番)
    for i, s in enumerate(kept, 1):
        s["id"] = i

    SHOPS_PATH.write_text(
        json.dumps(kept, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REMOVED_PATH.write_text(
        json.dumps(removed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # --- レポート ---
    print()
    print("=" * 50)
    print("登録結果")
    print("=" * 50)
    print(f"  登録: {len(kept)} 件")
    print(f"    うち tag自動推論: {inferred_count} 件")
    print(f"  除外: {len(removed)} 件")
    if reason_counts:
        for reason, c in reason_counts.items():
            print(f"    - {reason}: {c}")
    print()

    # タグ別件数
    tag_counter: Counter[str] = Counter()
    for s in kept:
        for t in s.get("tags", []):
            tag_counter[t] += 1
    print("タグ別件数:")
    if tag_counter:
        for tag, c in sorted(tag_counter.items(), key=lambda x: -x[1]):
            print(f"  {tag}: {c}")
    else:
        print("  (なし)")
    print()

    # スコア別分布
    score_counter: Counter[int] = Counter()
    for s in kept:
        score_counter[int(s.get("score", 3))] += 1
    print("スコア別分布:")
    for sc in sorted(score_counter.keys(), reverse=True):
        bar = "★" * sc
        print(f"  [{sc}] {bar}: {score_counter[sc]} 件")
    print()

    # エリア・ジャンル別
    area_counter: Counter[str] = Counter()
    genre_counter: Counter[str] = Counter()
    for s in kept:
        area_counter[s.get("area", "?")] += 1
        genre_counter[s.get("genre", "?")] += 1
    print("エリア別:")
    for a, c in area_counter.most_common():
        print(f"  {a}: {c}")
    print()
    print("ジャンル別:")
    for g, c in genre_counter.most_common():
        print(f"  {g}: {c}")
    print()

    # Place Photos 月次使用回数
    usage = load_photos_usage()
    print("Place Photos 使用状況:")
    print(f"  月: {usage.get('month')}")
    print(f"  使用回数: {usage.get('count', 0)} / 5000")
    print()

    print(f"出力: {SHOPS_PATH}")
    if removed:
        print(f"除外データ: {REMOVED_PATH}")


if __name__ == "__main__":
    main()
