"""
shops_raw.json の各店舗について
  A) Place Photos API で画像をダウンロード (public/photos/ に保存)
  B) Gemini 2.5 Flash-Lite で子連れ対応情報をリサーチ
  C) 結果を data/shops.json に追記 (place_id で重複チェック)

使い方:
    export GOOGLE_PLACES_API_KEY="AIza..."
    export GEMINI_API_KEY="AIza..."
    python3 scripts/research_shops.py

中断耐性:
    processed.json で処理済み place_id を管理
    途中で止めても次回は続きから再開
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR / "shops_raw.json"
PROCESSED_PATH = SCRIPT_DIR / "processed.json"
PHOTOS_USAGE_PATH = SCRIPT_DIR / "photos_usage.json"
SHOPS_PATH = ROOT / "data" / "shops.json"
PHOTOS_DIR = ROOT / "public" / "photos"

# Gemini
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GEMINI_DAILY_LIMIT = 1000
GEMINI_WARN_THRESHOLD = 900

# Places Photos
PHOTOS_MONTHLY_LIMIT = 5000
PHOTOS_WARN_THRESHOLD = 4500

# レート制御
GEMINI_SLEEP = float(os.environ.get("GEMINI_SLEEP", "2.5"))
PHOTO_SLEEP = float(os.environ.get("PHOTO_SLEEP", "0.5"))

PROMPT_TMPL = """以下の飲食店について、Googleマップの実際のクチコミから
子連れ対応情報を抽出してJSONのみで返してください(説明文・マークダウン不要)。

店名:{name}
住所:{address}

【クチコミ】
{reviews}

このクチコミのみを根拠に判定してください。クチコミに明示的な記述がない情報は推測しない。

返却フォーマット:
{{
  "genre": "カフェ/和食/洋食/イタリアン/その他 のいずれか",
  "tags": ["ベビーカーOK","座敷あり","キッズチェアあり","個室あり","騒いでもOK","子供メニューあり"] ※該当するもののみ・最大4つ,
  "description": "子連れ目線の紹介文(50文字以内)",
  "score": 子連れ安心度(1〜5の整数),
  "tabelog_url": "食べログURL(なければ空文字)",
  "is_chain": true or false,
  "evidence": ["根拠となったクチコミ引用(30文字程度)の配列"]
}}
"""

PLACES_FIELD_MASK_REVIEWS = "id,displayName,reviews"
MAX_REVIEWS = 5

VALID_GENRES = {"カフェ", "和食", "洋食", "イタリアン", "その他"}

# 名前ベースの除外（Hotpepper 経路と統一）
try:
    sys.path.insert(0, str(SCRIPT_DIR))
    from get_shops_hotpepper import (  # type: ignore
        is_chain as _is_chain,
        has_excluded_name as _has_excluded_name,
        EXCLUDED_GENRE_KEYWORDS_GPLACES as _EXCLUDED_GENRE_KEYWORDS_GPLACES,
    )

    def _is_excluded_name(name: str) -> bool:
        if not name:
            return False
        if _is_chain(name):
            return True
        if _has_excluded_name(name):
            return True
        if any(kw in name for kw in _EXCLUDED_GENRE_KEYWORDS_GPLACES):
            return True
        return False
except Exception:
    def _is_excluded_name(name: str) -> bool:  # フォールバック
        return False
VALID_TAGS = {
    "ベビーカーOK", "座敷あり", "キッズチェアあり",
    "個室あり", "騒いでもOK", "子供メニューあり",
}


# ---------- ユーティリティ ----------
def load_keys() -> tuple[str, str]:
    places_key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not places_key:
        print("ERROR: GOOGLE_PLACES_API_KEY 未設定", file=sys.stderr)
        sys.exit(1)
    if not gemini_key:
        print("ERROR: GEMINI_API_KEY 未設定", file=sys.stderr)
        sys.exit(1)
    return places_key, gemini_key


def load_processed() -> set[str]:
    if not PROCESSED_PATH.exists():
        return set()
    try:
        return set(json.loads(PROCESSED_PATH.read_text(encoding="utf-8")))
    except Exception:
        return set()


def save_processed(processed: set[str]) -> None:
    PROCESSED_PATH.write_text(
        json.dumps(sorted(processed), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_photos_usage() -> dict:
    """月別の Place Photos 使用回数を記録."""
    now_month = datetime.date.today().strftime("%Y-%m")
    if PHOTOS_USAGE_PATH.exists():
        try:
            data = json.loads(PHOTOS_USAGE_PATH.read_text(encoding="utf-8"))
            if data.get("month") == now_month:
                return data
        except Exception:
            pass
    return {"month": now_month, "count": 0}


def save_photos_usage(usage: dict) -> None:
    PHOTOS_USAGE_PATH.write_text(
        json.dumps(usage, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_existing_shops() -> list[dict]:
    if not SHOPS_PATH.exists():
        return []
    try:
        d = json.loads(SHOPS_PATH.read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except Exception:
        return []


def save_shops(shops: list[dict]) -> None:
    SHOPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SHOPS_PATH.write_text(
        json.dumps(shops, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------- STEP A: Place Photos ----------
def download_photo(api_key: str, photo_name: str, place_id: str) -> str:
    """
    Place Photos API で画像をダウンロードし public/photos/ に保存。
    戻り値: サイトで使える相対URL (例: /photos/ChIJ....jpg), 失敗時は空文字
    """
    if not photo_name:
        return ""

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    # 拡張子は jpg 固定 (Google の画像は jpeg で返る)
    filename = f"{place_id}.jpg"
    out_file = PHOTOS_DIR / filename

    # 既にファイルがあれば再DLしない
    if out_file.exists():
        return f"/photos/{filename}"

    url = (
        f"https://places.googleapis.com/v1/{photo_name}/media"
        f"?maxWidthPx=800&key={api_key}"
    )
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=30) as res:
            content = res.read()
            if not content:
                return ""
            out_file.write_bytes(content)
            return f"/photos/{filename}"
    except error.HTTPError as e:
        print(f"    [Photos {e.code}] {e.read().decode('utf-8', errors='replace')[:150]}",
              file=sys.stderr)
        return ""
    except Exception as e:
        print(f"    [Photos err] {e}", file=sys.stderr)
        return ""


# ---------- STEP B: Gemini ----------
def extract_json(text: str) -> dict | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    s = text.find("{")
    e = text.rfind("}")
    if s == -1 or e == -1 or e < s:
        return None
    try:
        return json.loads(text[s:e + 1])
    except Exception:
        return None


def fetch_reviews(api_key: str, place_id: str) -> list[dict]:
    """Place Details から reviews を取得."""
    url = f"https://places.googleapis.com/v1/places/{place_id}?languageCode=ja&regionCode=JP"
    req = request.Request(
        url, method="GET",
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": PLACES_FIELD_MASK_REVIEWS,
        },
    )
    try:
        with request.urlopen(req, timeout=20) as res:
            payload = json.loads(res.read().decode("utf-8"))
            return payload.get("reviews", []) or []
    except Exception as e:
        print(f"    [Reviews err] {e}", file=sys.stderr)
        return []


def format_reviews(reviews: list[dict]) -> str:
    lines: list[str] = []
    for i, r in enumerate(reviews[:MAX_REVIEWS], 1):
        text = (r.get("originalText") or r.get("text") or {}).get("text", "")
        if not text:
            continue
        rating = r.get("rating", "?")
        text = text.replace("\n", " ").strip()
        if len(text) > 500:
            text = text[:500] + "…"
        lines.append(f"[{i}] ★{rating} {text}")
    return "\n".join(lines) if lines else "(クチコミなし)"


def gemini_research(api_key: str, name: str, address: str, reviews_text: str) -> dict | None:
    prompt = PROMPT_TMPL.format(name=name, address=address, reviews=reviews_text)
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    req = request.Request(
        f"{GEMINI_ENDPOINT}?key={api_key}",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=60) as res:
            payload = json.loads(res.read().decode("utf-8"))
    except error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        print(f"    [Gemini {e.code}] {body_err[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"    [Gemini err] {e}", file=sys.stderr)
        return None

    try:
        parts = payload["candidates"][0]["content"]["parts"]
        text = "\n".join(p.get("text", "") for p in parts if "text" in p)
    except Exception:
        return None
    return extract_json(text)


def sanitize(r: dict) -> dict:
    genre = r.get("genre") or "その他"
    if genre not in VALID_GENRES:
        genre = "その他"
    tags = [t for t in (r.get("tags") or []) if isinstance(t, str) and t in VALID_TAGS]
    tags = list(dict.fromkeys(tags))[:4]
    desc = r.get("description") or ""
    if not isinstance(desc, str):
        desc = ""
    if len(desc) > 80:
        desc = desc[:80]
    try:
        score = int(r.get("score", 3))
    except Exception:
        score = 3
    score = max(1, min(5, score))
    tabelog = r.get("tabelog_url") or ""
    if not isinstance(tabelog, str):
        tabelog = ""
    is_chain_val = bool(r.get("is_chain", False))
    evidence = [str(x)[:120] for x in (r.get("evidence") or []) if x]
    return {
        "genre": genre,
        "tags": tags,
        "description": desc,
        "score": score,
        "tabelog_url": tabelog,
        "is_chain": is_chain_val,
        "evidence": evidence,
    }


# ---------- Main ----------
def main() -> None:
    places_key, gemini_key = load_keys()

    if not RAW_PATH.exists():
        print(f"ERROR: {RAW_PATH} が見つかりません。先に get_shops.py を実行してください。",
              file=sys.stderr)
        sys.exit(1)

    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    processed = load_processed()
    usage = load_photos_usage()
    shops = load_existing_shops()
    existing_ids = {s.get("place_id") for s in shops if isinstance(s, dict) and s.get("place_id")}

    print("=" * 50)
    print("BOKUMO research_shops.py")
    print("=" * 50)
    print(f"入力: {len(raw)} 件")
    print(f"処理済み(processed.json): {len(processed)} 件")
    print(f"既存 shops.json: {len(shops)} 件")
    print(f"Place Photos 今月使用: {usage['count']}/{PHOTOS_MONTHLY_LIMIT}")
    print()

    gemini_count = 0
    success = 0
    failed = 0
    skipped = 0

    next_id = max((s.get("id", 0) for s in shops), default=0) + 1

    try:
        for i, r in enumerate(raw, 1):
            pid = r.get("place_id")
            name = r.get("name", "")
            address = r.get("address", "")
            lat = r.get("lat")
            lng = r.get("lng")
            photo_ref = r.get("photo_reference", "")

            if not pid or not name:
                skipped += 1
                continue

            if pid in processed:
                print(f"[{i}/{len(raw)}] SKIP(処理済): {name}")
                skipped += 1
                continue

            # 名前ベースのフィルタ（チェーン・夜業態・居酒屋等を除外）
            if _is_excluded_name(name):
                print(f"[{i}/{len(raw)}] SKIP(NG): {name}")
                processed.add(pid)
                save_processed(processed)
                skipped += 1
                continue

            # Gemini 日次上限警告
            if gemini_count >= GEMINI_DAILY_LIMIT:
                print(f"\n⚠️  Gemini 1日{GEMINI_DAILY_LIMIT}件上限到達。中断。")
                break
            if gemini_count >= GEMINI_WARN_THRESHOLD and gemini_count % 10 == 0:
                print(f"   ⚠️  Gemini 残り枠わずか: {gemini_count}/{GEMINI_DAILY_LIMIT}")

            # Place Photos 月次上限警告
            if usage["count"] >= PHOTOS_MONTHLY_LIMIT:
                print(f"\n⚠️  Place Photos 月次 {PHOTOS_MONTHLY_LIMIT} 件上限到達。画像DLは停止しGeminiのみ実行。")
            if usage["count"] >= PHOTOS_WARN_THRESHOLD and usage["count"] % 50 == 0:
                print(f"   ⚠️  Place Photos 残り枠わずか: {usage['count']}/{PHOTOS_MONTHLY_LIMIT}")

            print(f"[{i}/{len(raw)}] {name}")

            # --- STEP A: Photo ダウンロード ---
            image_url = ""
            if photo_ref and usage["count"] < PHOTOS_MONTHLY_LIMIT:
                image_url = download_photo(places_key, photo_ref, pid)
                if image_url:
                    usage["count"] += 1
                    save_photos_usage(usage)
                    print(f"    📷 image: {image_url}")
                time.sleep(PHOTO_SLEEP)

            # --- STEP B: Reviews 取得 → Gemini リサーチ ---
            reviews = fetch_reviews(places_key, pid)
            reviews_text = format_reviews(reviews)
            time.sleep(0.3)

            research = gemini_research(gemini_key, name, address, reviews_text)
            gemini_count += 1
            time.sleep(GEMINI_SLEEP)

            if not research:
                print("    → Gemini解析失敗、スキップ")
                failed += 1
                continue

            clean = sanitize(research)

            # qualifying tag が1つもない店は採用しない（クチコミから子連れ要素を抽出できなかった）
            if not clean["tags"]:
                print(f"    → SKIP: 子連れタグ抽出できず")
                processed.add(pid)
                save_processed(processed)
                skipped += 1
                continue

            # --- STEP C: shops.json に追記/更新 ---
            entry = {
                "place_id": pid,
                "name": name,
                "area": "宮の森" if ("宮ケ丘" in address or "宮の森" in address) else "円山",
                "genre": clean["genre"],
                "tags": clean["tags"],
                "description": clean["description"],
                "score": clean["score"],
                "lat": lat,
                "lng": lng,
                "tabelog_url": clean["tabelog_url"],
                "image_url": image_url or "",
                "is_chain": clean["is_chain"],
                "evidence": clean["evidence"],
            }

            if pid in existing_ids:
                for j, s in enumerate(shops):
                    if s.get("place_id") == pid:
                        entry["id"] = s.get("id", next_id)
                        shops[j] = {**s, **entry}
                        break
            else:
                entry["id"] = next_id
                shops.append(entry)
                existing_ids.add(pid)
                next_id += 1

            processed.add(pid)

            # 1件ごと保存 (中断耐性)
            save_shops(shops)
            save_processed(processed)

            success += 1
            tag_str = "/".join(clean["tags"]) if clean["tags"] else "タグなし"
            chain_mark = " [CHAIN]" if clean["is_chain"] else ""
            print(f"    → [★{clean['score']}] {clean['genre']} / {tag_str}{chain_mark}")
            print(f"      {clean['description']}")
            print(f"    (本日Gemini: {gemini_count} / 今月Photos: {usage['count']})")

    except KeyboardInterrupt:
        print("\n中断されました。ここまでの結果は保存済みです。")

    print()
    print("=" * 50)
    print("処理結果")
    print("=" * 50)
    print(f"  成功     : {success} 件")
    print(f"  スキップ : {skipped} 件")
    print(f"  失敗     : {failed} 件")
    print(f"  本日Gemini使用: {gemini_count} 件")
    print(f"  今月Photos使用: {usage['count']}/{PHOTOS_MONTHLY_LIMIT} 件")
    print(f"  最終 shops.json: {len(shops)} 件")
    print()
    print(f"出力: {SHOPS_PATH}")
    print(f"進捗: {PROCESSED_PATH}")


if __name__ == "__main__":
    main()
