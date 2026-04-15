"""
data/shops.json を子連れ特化フィルタで絞り込む。

ルール:
  - evidence (クチコミ引用) の中にポジティブな子連れキーワードが
    1つ以上含まれる店のみ残す
  - score が 2 以下の店は除外 (不向きな店)
  - description やネガティブキーワード単体("入店不可"等)も除外判定
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOPS_PATH = ROOT / "data" / "shops.json"
REMOVED_PATH = ROOT / "data" / "shops_removed.json"

POSITIVE_KEYWORDS = [
    "子連れ",
    "子ども",
    "子供",
    "こども",
    "赤ちゃん",
    "離乳食",
    "ミルク",
    "ベビー",
    "キッズ",
    "子育て",
    "親子",
    "幼児",
    "ハイチェア",
    "キッズチェア",
    "お子様",
    "お子さん",
]

# ネガティブ文脈 (これを含む文はポジティブ判定から除外)
NEGATIVE_PATTERNS = [
    r"入店.{0,5}(不可|出来ません|できません|お断り|禁止)",
    r"(子供|こども|小学生|未就学児|幼児).{0,10}(不可|出来ません|できません|お断り|禁止|NG)",
    r"未満.{0,5}(不可|出来ません|できません|入れません)",
]


def has_positive_child_evidence(evidences: list[str]) -> tuple[bool, list[str]]:
    """
    evidences の中にポジティブな子連れ記述があるか判定。
    戻り値: (マッチしたか, マッチしたエビデンス文の配列)
    """
    matched: list[str] = []
    for ev in evidences:
        if not isinstance(ev, str):
            continue
        # ネガティブ文脈チェック
        if any(re.search(p, ev) for p in NEGATIVE_PATTERNS):
            continue
        # ポジティブキーワード
        if any(kw in ev for kw in POSITIVE_KEYWORDS):
            matched.append(ev)
    return (len(matched) > 0, matched)


def main() -> None:
    shops = json.loads(SHOPS_PATH.read_text(encoding="utf-8"))
    print(f"入力: {len(shops)} 店舗")
    print()

    kept: list[dict] = []
    removed: list[dict] = []

    for s in shops:
        name = s.get("name", "")
        score = s.get("score", 3)
        evidences = s.get("evidence") or []

        ok, matched = has_positive_child_evidence(evidences)

        if score <= 2:
            reason = f"score={score} (子連れに不向き)"
            removed.append({**s, "_removed_reason": reason})
            print(f"  ❌ {name}  ({reason})")
            continue

        if not ok:
            reason = "evidenceに子連れ関連記述なし"
            removed.append({**s, "_removed_reason": reason})
            print(f"  ❌ {name}  ({reason})")
            continue

        print(f"  ✅ {name}  (マッチ: {len(matched)}件)")
        for m in matched:
            print(f"       ▸ {m}")
        kept.append(s)

    # ID 振り直し
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

    print()
    print(f"採用: {len(kept)} 店舗 → {SHOPS_PATH}")
    print(f"除外: {len(removed)} 店舗 → {REMOVED_PATH}")


if __name__ == "__main__":
    main()
