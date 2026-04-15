#!/usr/bin/env python3
"""
merge_results.py - Geminiクチコミ解析と公式サイト/Instagramスクレイピングの結果を統合する。

Input:
  scripts/pipeline/kid_friendly.json      (Geminiクチコミ解析結果)
  scripts/pipeline/kid_friendly_web.json  (公式サイト/Instagram結果)

Output:
  scripts/pipeline/kid_friendly_merged.json (統合結果)

統合ロジック:
  - place_id で照合
  - どちらかに存在すれば採用
  - 両方に存在する場合:
    - tags: 両方をマージ（重複除去）
    - score: 高い方を採用
    - evidence: 両方を結合（source で区別）
    - description: Gemini側を優先（空なら公式サイト側）
"""

import json
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
GEMINI_PATH = BASE_DIR / "kid_friendly.json"
WEB_PATH = BASE_DIR / "kid_friendly_web.json"
OUTPUT_PATH = BASE_DIR / "kid_friendly_merged.json"

VALID_TAGS = {
    "ベビーカーOK", "座敷/小上がりあり", "キッズチェアあり",
    "個室あり", "子連れOK", "子供メニューあり",
}


def load_json(path, default=None):
    if not path.exists():
        return default if default is not None else []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else []


def merge_tags(tags_a, tags_b):
    """2つのタグリストをマージ（重複除去、順序維持）"""
    merged = list(tags_a or [])
    for t in (tags_b or []):
        if t not in merged and t in VALID_TAGS:
            merged.append(t)
    return merged


def merge_evidence(ev_a, ev_b, source_a="クチコミ", source_b="公式サイト"):
    """evidenceを結合し、重複を除去"""
    seen = set()
    merged = []
    for ev in (ev_a or []):
        if isinstance(ev, str) and ev not in seen:
            seen.add(ev)
            merged.append(ev)
    for ev in (ev_b or []):
        if isinstance(ev, str) and ev not in seen:
            seen.add(ev)
            merged.append(ev)
    return merged


def main():
    gemini_data = load_json(GEMINI_PATH, [])
    web_data = load_json(WEB_PATH, [])

    print("=" * 60)
    print("BOKUMO merge_results.py")
    print("=" * 60)
    print(f"Geminiクチコミ結果:     {len(gemini_data)} 件")
    print(f"公式サイト/Instagram結果: {len(web_data)} 件")
    print()

    # place_id でインデックス化
    gemini_map = {}
    for s in gemini_data:
        pid = s.get("place_id", "")
        if pid:
            gemini_map[pid] = s

    web_map = {}
    for s in web_data:
        pid = s.get("place_id", "")
        if pid:
            web_map[pid] = s

    # 全 place_id を集める
    all_ids = set(gemini_map.keys()) | set(web_map.keys())

    both = 0
    gemini_only = 0
    web_only = 0
    merged = []

    for pid in all_ids:
        g = gemini_map.get(pid)
        w = web_map.get(pid)

        if g and w:
            # 両方にある → マージ
            result = {**g}  # Gemini側をベースにコピー
            result["tags"] = merge_tags(g.get("tags", []), w.get("tags", []))
            result["score"] = max(g.get("score", 3), w.get("score", 3))
            result["evidence"] = merge_evidence(
                g.get("evidence", []),
                w.get("evidence", []),
            )
            result["description"] = g.get("description") or w.get("description", "")
            result["source"] = "both"
            merged.append(result)
            both += 1

        elif g:
            # Geminiのみ
            g["source"] = "gemini"
            merged.append(g)
            gemini_only += 1

        elif w:
            # 公式サイトのみ → 新規発見
            w["source"] = "website"
            merged.append(w)
            web_only += 1

    # 保存
    OUTPUT_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # レポート
    tag_counter = Counter()
    score_counter = Counter()
    source_counter = Counter()
    for s in merged:
        for t in s.get("tags", []):
            tag_counter[t] += 1
        score_counter[s.get("score", 3)] += 1
        source_counter[s.get("source", "?")] += 1

    print("=" * 60)
    print("統合結果")
    print("=" * 60)
    print(f"  合計:              {len(merged)} 件")
    print(f"  両方で発見:         {both} 件")
    print(f"  Geminiのみ:        {gemini_only} 件")
    print(f"  公式サイトのみ(新規): {web_only} 件")
    print()
    print("ソース別:")
    for src, c in source_counter.most_common():
        print(f"  {src}: {c}")
    print()
    print("タグ別:")
    for t, c in tag_counter.most_common():
        print(f"  {t}: {c}")
    print()
    print("スコア別:")
    for sc in sorted(score_counter.keys(), reverse=True):
        print(f"  ★{sc}: {score_counter[sc]}")
    print()
    print(f"出力: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
