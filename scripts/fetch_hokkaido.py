"""北海道全域を Text Search でカバーし、飲食店候補を集める（fetch_sapporo.py の拡張版）。

- ロット指定で札幌 / 道内主要 / 道内その他 を分けて取得可能
- 各エリア × 18ジャンルキーワード で複数クエリ発行（1ページ20件まで）
- 既存 data/shops.json と重複する place_id は除外
- 既存の名前/ジャンル/typeフィルタを流用（fetch_sapporo.py から import）
- 出力: scripts/shops_raw.json（既存形式・research_shops.py で続行可能）

使い方:
    python3 scripts/fetch_hokkaido.py --lot 1   # 札幌10区
    python3 scripts/fetch_hokkaido.py --lot 2   # 道内主要7市
    python3 scripts/fetch_hokkaido.py --lot 3   # 道内その他8市町
    python3 scripts/fetch_hokkaido.py --dry-run --lot 1   # 規模試算のみ（API叩かない）
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR / "shops_raw.json"
SHOPS_PATH = ROOT / "data" / "shops.json"

# fetch_sapporo.py の関数群を流用
from fetch_sapporo import (
    text_search, load_key,
    is_chain, has_excluded_name,
    is_excluded_by_genre_keyword, is_excluded_by_place_type,
)

# ロット定義
LOTS: dict[int, dict] = {
    1: {
        "name": "札幌10区",
        "queries": [f"札幌市{w}" for w in (
            "中央区", "北区", "東区", "白石区", "厚別区",
            "豊平区", "清田区", "南区", "西区", "手稲区",
        )],
    },
    2: {
        "name": "道内主要7市",
        "queries": [f"{c}" for c in (
            "函館市", "旭川市", "帯広市", "釧路市",
            "北見市", "苫小牧市", "室蘭市",
        )],
    },
    3: {
        "name": "道内その他8市町",
        "queries": [f"{c}" for c in (
            "登別市", "千歳市", "江別市", "石狩市",
            "岩見沢市", "富良野市", "名寄市", "倶知安町",
        )],
    },
}

# 子連れ向きを意識したジャンルキーワード（ベーカリー・パンケーキは除外）
GENRE_KEYWORDS = [
    "カフェ", "ファミリーレストラン", "ラーメン", "うどん 蕎麦",
    "回転寿司", "焼肉", "とんかつ", "中華料理",
    "ハンバーグ", "パン屋",
    "寿司", "海鮮", "定食", "洋食",
    "パスタ", "お好み焼き", "スイーツ", "カレー",
]

SLEEP_SEC = 0.5
TEXT_SEARCH_COST = 0.032  # USD per request (Pro SKU)
PLACE_DETAILS_COST = 0.017
PHOTO_COST = 0.007
ESTIMATED_PER_QUERY = 14  # サンプリング実測の平均純増
GEMINI_PASS_RATE = 0.13   # 過去通過率


def estimate_for_lots(lot_ids: list[int]) -> None:
    """ドライラン: コスト・候補数を試算（API は叩かない）"""
    total_queries = 0
    for lid in lot_ids:
        lot = LOTS[lid]
        n_queries = len(lot["queries"]) * len(GENRE_KEYWORDS)
        total_queries += n_queries
        est_candidates = n_queries * ESTIMATED_PER_QUERY
        est_pass = int(est_candidates * GEMINI_PASS_RATE)
        ts_cost = n_queries * TEXT_SEARCH_COST
        downstream = est_candidates * (PLACE_DETAILS_COST + PHOTO_COST)
        print(f"--- ロット{lid}: {lot['name']} ---")
        print(f"  エリア×ジャンル: {len(lot['queries'])} × {len(GENRE_KEYWORDS)} = {n_queries} クエリ")
        print(f"  推定候補(純増): {est_candidates} 件")
        print(f"  推定追加(13%通過): {est_pass} 店")
        print(f"  Text Search コスト: ${ts_cost:.2f}")
        print(f"  後続 Place Details + Photos コスト: ${downstream:.2f}")
        print(f"  ロット小計: ${ts_cost + downstream:.2f}")
        print()
    print(f"=== 合計 {total_queries} クエリ ===")


def fetch_one_lot(api_key: str, lot_id: int, existing_pids: set[str]) -> dict[str, dict]:
    lot = LOTS[lot_id]
    print(f"=== ロット{lot_id}: {lot['name']} ===")

    all_places: dict[str, dict] = {}
    rejected = {"chain": 0, "name": 0, "genre": 0, "type": 0, "duplicate": 0}
    total_calls = 0

    for area in lot["queries"]:
        area_added = 0
        for genre in GENRE_KEYWORDS:
            query = f"{area} {genre}"
            data = text_search(api_key, query, "")
            total_calls += 1
            places = data.get("places", []) or []
            added = 0
            for p in places:
                pid = p.get("id")
                if not pid:
                    continue
                if pid in existing_pids or pid in all_places:
                    rejected["duplicate"] += 1
                    continue
                nm = (p.get("displayName") or {}).get("text") or ""
                if is_chain(nm):
                    rejected["chain"] += 1
                    continue
                if has_excluded_name(nm):
                    rejected["name"] += 1
                    continue
                if is_excluded_by_genre_keyword(nm):
                    rejected["genre"] += 1
                    continue
                if is_excluded_by_place_type(p.get("types") or []):
                    rejected["type"] += 1
                    continue
                all_places[pid] = p
                added += 1
                area_added += 1
            print(f"  {query}: 取得 {len(places)} → 純増 +{added} (累計 {len(all_places)})")
            time.sleep(SLEEP_SEC)
        print(f"--- {area} 終了: +{area_added} (ロット累計 {len(all_places)}) ---")

    cost = total_calls * TEXT_SEARCH_COST
    print()
    print(f"✅ ロット{lot_id} 完了: 純増候補 {len(all_places)} 件 / Text Search {total_calls}回 / 約 ${cost:.2f}")
    print(f"   除外内訳: {rejected}")
    return all_places


def main() -> None:
    ap = argparse.ArgumentParser(description="北海道全域 飲食店候補発掘")
    ap.add_argument("--lot", type=int, choices=[1, 2, 3], action="append",
                    help="実行するロット番号 (複数指定可。未指定なら全ロット)")
    ap.add_argument("--dry-run", action="store_true",
                    help="API を叩かず規模試算だけ表示")
    args = ap.parse_args()

    lot_ids = sorted(set(args.lot or [1, 2, 3]))

    if args.dry_run:
        print("=== ドライラン（API課金なし）===\n")
        estimate_for_lots(lot_ids)
        return

    api_key = load_key()

    existing_pids: set[str] = set()
    if SHOPS_PATH.exists():
        for s in json.loads(SHOPS_PATH.read_text(encoding="utf-8")):
            pid = s.get("place_id")
            if pid:
                existing_pids.add(pid)
    print(f"既存 shops.json place_id: {len(existing_pids)} 件\n")

    # 既存 shops_raw.json を読んで未処理を引き継ぐ
    prior_places: list[dict] = []
    if RAW_PATH.exists():
        prior = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        prior_places = prior.get("places", []) if isinstance(prior, dict) else prior
    print(f"既存 shops_raw.json: {len(prior_places)} 件（追記モード）\n")
    prior_pids = {p.get("id") for p in prior_places if p.get("id")}

    new_places: dict[str, dict] = {}
    for lid in lot_ids:
        got = fetch_one_lot(api_key, lid, existing_pids | prior_pids | new_places.keys())
        new_places.update(got)
        time.sleep(SLEEP_SEC)

    # 追記保存
    merged = prior_places + list(new_places.values())
    RAW_PATH.write_text(
        json.dumps({"places": merged}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print()
    print(f"✅ 全ロット完了: 今回新規 {len(new_places)} 件 / 累計 {len(merged)} 件")
    print(f"   出力: {RAW_PATH}")
    print(f"   次: python3 scripts/research_shops.py で Gemini 判定 + 写真取得")


if __name__ == "__main__":
    main()
