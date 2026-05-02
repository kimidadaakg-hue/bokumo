"""札幌10区を Text Search でカバーし、飲食店候補を集める。

- 10区 × ジャンルキーワード で複数クエリ発行
- 各クエリ最大60件 → 600件超 取得目標
- 既存 data/shops.json と重複する place_id は除外
- 出力: scripts/shops_raw.json (既存 fetch_shops.py と同じ形式) → research_shops.py で続行可能
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR / "shops_raw.json"
SHOPS_PATH = ROOT / "data" / "shops.json"
ENV_FILE = ROOT / ".env.local"

API_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id", "places.displayName", "places.formattedAddress",
    "places.location", "places.primaryType", "places.types",
])

# 札幌10区
WARDS = [
    "中央区", "北区", "東区", "白石区", "厚別区",
    "豊平区", "清田区", "南区", "西区", "手稲区",
]

# 子連れ向きを意識したジャンルキーワード
GENRE_KEYWORDS = [
    "カフェ",
    "ファミリーレストラン",
    "ラーメン",
    "うどん 蕎麦",
    "回転寿司",
    "焼肉",
    "とんかつ",
    "中華料理",
    "ハンバーグ",
    "パン屋",
]

SLEEP_SEC = 0.5
MAX_PAGES_PER_QUERY = 3  # 最大60件 (20×3ページ)

# Hotpepper 経路と統一: チェーン店・夜の業態を除外
from get_shops_hotpepper import (
    CHAIN_KEYWORDS, EXCLUDED_GENRE_KEYWORDS, EXCLUDED_NAME_KEYWORDS,
    is_chain, has_excluded_name,
)


def is_excluded_by_genre_keyword(name: str) -> bool:
    return any(kw in name for kw in EXCLUDED_GENRE_KEYWORDS)


def is_excluded_by_place_type(types: list[str]) -> bool:
    """Google Places の type が bar / night_club 等なら除外"""
    bad_types = {"bar", "night_club", "liquor_store"}
    return any(t in bad_types for t in (types or []))


def load_key() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("GOOGLE_PLACES_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GOOGLE_PLACES_API_KEY not found in .env.local")


def text_search(api_key: str, query: str, page_token: str = "") -> dict:
    body: dict[str, Any] = {
        "textQuery": query,
        "languageCode": "ja",
        "regionCode": "JP",
        "pageSize": 20,
    }
    if page_token:
        body["pageToken"] = page_token
    req = request.Request(
        API_URL,
        method="POST",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
    )
    try:
        with request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  [HTTP {e.code}] {body[:200]}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"  [err] {e}", file=sys.stderr)
        return {}


def main() -> None:
    api_key = load_key()

    # 既存 place_id
    existing_pids: set[str] = set()
    if SHOPS_PATH.exists():
        for s in json.loads(SHOPS_PATH.read_text(encoding="utf-8")):
            pid = s.get("place_id")
            if pid:
                existing_pids.add(pid)
    print(f"既存 place_id: {len(existing_pids)} 件")

    all_places: dict[str, dict] = {}
    total_calls = 0

    for ward in WARDS:
        for genre in GENRE_KEYWORDS:
            query = f"札幌市{ward} {genre}"
            page_token = ""
            for page in range(MAX_PAGES_PER_QUERY):
                data = text_search(api_key, query, page_token)
                total_calls += 1
                places = data.get("places", []) or []
                added = 0
                for p in places:
                    pid = p.get("id")
                    if not pid or pid in existing_pids or pid in all_places:
                        continue
                    nm = (p.get("displayName") or {}).get("text") or ""
                    if is_chain(nm):
                        continue
                    if has_excluded_name(nm):
                        continue
                    if is_excluded_by_genre_keyword(nm):
                        continue
                    if is_excluded_by_place_type(p.get("types") or []):
                        continue
                    all_places[pid] = p
                    added += 1
                page_token = data.get("nextPageToken", "")
                print(f"  {query} (page {page+1}): +{added} (累計 {len(all_places)})")
                if not page_token:
                    break
                time.sleep(SLEEP_SEC)
            time.sleep(SLEEP_SEC)
        # ward 区切りで進捗表示
        print(f"--- {ward} 終了: 累計 {len(all_places)} 件 / Text Search呼出 {total_calls} 回 ---")

    # shops_raw.json 形式で保存（fetch_shops.py / research_shops.py 互換）
    raw_list = list(all_places.values())
    RAW_PATH.write_text(
        json.dumps({"places": raw_list}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    cost = total_calls * 0.032  # Text Search Pro
    print()
    print(f"✅ 候補取得: {len(raw_list)} 店 (Text Search {total_calls} 回, 概算 ${cost:.2f})")
    print(f"   出力: {RAW_PATH}")
    print(f"   次: python3 scripts/research_shops.py で Gemini 判定 + 写真取得")


if __name__ == "__main__":
    main()
