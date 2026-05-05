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
子連れ（特に乳幼児〜未就学児）対応情報を抽出してJSONのみで返してください(説明文・マークダウン不要)。

店名:{name}
住所:{address}

【クチコミ】
{reviews}

このクチコミのみを根拠に判定してください。**以下のルールを厳守**：

1. 「家族で来た」「家族連れ多い」「友人と」「親族で」だけでは子連れタグを付けない
2. 単に「子供」「子ども」「お子さん」と書かれていても、年齢が分からない（中学生以上の可能性）
   → これだけでは根拠不足。小学校高学年以上は「子連れOK店」の判定に使えない
3. **以下のいずれかが明示されている場合のみ**タグを付ける：
   a) **乳幼児・未就学児を示す語**：赤ちゃん/ベビー/乳児/離乳食/おむつ/ベビーカー/抱っこ紐/ストローラー/小さい子/未就学/幼児/4歳以下/3歳以下/2歳以下/1歳/0歳/イヤイヤ期
   b) **明確な設備・サービス**：キッズチェア/子供用椅子/ベビーチェア/ハイチェア/お子様メニュー/キッズメニュー/お子様ランチ/座敷/個室/おむつ替え台/キッズスペース/お絵かきセット
4. 上記のキーワードがない場合は tags は空 [] で返す（推測禁止）
5. evidence にはタグの根拠となったクチコミの**該当部分**を必ず含める

返却フォーマット:
{{
  "genre": "カフェ/和食/洋食/イタリアン/その他 のいずれか",
  "tags": ["ベビーカーOK","座敷あり","キッズチェアあり","個室あり","子連れOK","子供メニューあり"] ※上記ルール3を満たすもののみ・最大4つ,
  "description": "子連れ目線の紹介文(50文字以内)",
  "score": 子連れ安心度(1〜5の整数),
  "tabelog_url": "食べログURL(なければ空文字)",
  "is_chain": true or false,
  "evidence": ["根拠となったクチコミ引用(30文字程度)の配列"]
}}
"""

PLACES_FIELD_MASK_REVIEWS = (
    "id,displayName,reviews,photos,"
    "formattedAddress,rating,userRatingCount,"
    "regularOpeningHours,nationalPhoneNumber,websiteUri"
)
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
    "個室あり", "子連れOK", "子供メニューあり",
}

# === 子連れ判定の強根拠キーワード ===
# 「家族で来た」「子供と来た」だけ＝弱根拠なので不採用。
# 以下のいずれかが evidence(クチコミ引用) に含まれている場合のみ採用する。
# 子供は年齢が不明（中学生以上の可能性）なので慎重に。
STRONG_EVIDENCE_KEYWORDS = [
    # 乳幼児を示す語（年齢が小さいことが明確）
    "赤ちゃん", "ベビー", "乳児", "離乳食", "おむつ", "オムツ",
    "ベビーカー", "抱っこ紐", "ストローラー", "バウンサー",
    "小さい子", "小さなお子", "未就学", "幼児", "イヤイヤ期",
    "0歳", "1歳", "2歳", "3歳", "4歳",
    # 明確な子連れ向け設備・サービス
    "キッズチェア", "子供用椅子", "ベビーチェア", "ハイチェア",
    "お子様メニュー", "キッズメニュー", "お子様ランチ", "子供メニュー",
    "お子様ラーメン", "お子様プレート",
    "おむつ替え", "オムツ替え", "キッズスペース", "お絵かき", "おもちゃ",
    # 和室系（小さい子供を寝かせやすい / 走り回らせやすい）
    "座敷", "お座敷", "小上がり", "小上り",
    "掘り炬燵", "掘りごたつ", "個室",
    # ファミリー向け明示
    "ファミレス", "ファミリーレストラン",
]


def has_strong_evidence(evidence_list: list[str]) -> bool:
    """clean['evidence'] のクチコミ引用に強根拠キーワードが含まれているか"""
    if not evidence_list:
        return False
    text = " ".join(evidence_list)
    return any(kw in text for kw in STRONG_EVIDENCE_KEYWORDS)


def area_from_address(address: str) -> str:
    """住所から area 名（札幌XX区 / 函館 / 旭川 等）を推定.

    Place Details の住所は通常 '北海道札幌市中央区...' の順だが、
    たまに英語混じりの逆順 '... 函館市 北海道 040-0011' で返ってくる。
    両方の順序に対応する。

    「町」「村」は「本町」「東町」のような地名と衝突するので、
    必ず「○○郡△△町/村」のセットでのみ採用する。
    """
    import re
    if not address:
        return "不明"
    # 札幌の区
    if "札幌市" in address:
        m = re.search(r"札幌市\s*(\S+?区)", address)
        if m:
            return f"札幌{m.group(1)}"
    # 北海道内の市町村
    if "北海道" in address:
        # ① 「○○市」を最優先（北海道の市は必ず「○○市」表記）
        m = re.search(r"([^\s\d、,\-_／/]+市)", address)
        if m:
            return re.sub(r"市$", "", m.group(1))
        # ② 「○○郡△△町/村」のセット（「本町」のような地名混入防止）
        m = re.search(r"[^\s\d、,\-_／/]+郡\s*([^\s\d、,\-_／/]+[町村])", address)
        if m:
            return re.sub(r"[町村]$", "", m.group(1))
    return "不明"


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


def fetch_reviews(api_key: str, place_id: str) -> tuple[list[dict], dict]:
    """Place Details から reviews と店舗詳細(住所/評価/営業時間/電話/サイト)を取得."""
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
            reviews = payload.get("reviews", []) or []
            photos = payload.get("photos", []) or []
            first_photo_name = (photos[0].get("name", "") if photos else "")
            details = {
                "address": payload.get("formattedAddress", ""),
                "rating": payload.get("rating", 0),
                "rating_count": payload.get("userRatingCount", 0),
                "hours": (payload.get("regularOpeningHours", {}) or {}).get("weekdayDescriptions", []),
                "phone": payload.get("nationalPhoneNumber", ""),
                "website": payload.get("websiteUri", ""),
                "photo_name": first_photo_name,
            }
            return reviews, details
    except Exception as e:
        print(f"    [Reviews err] {e}", file=sys.stderr)
        return [], {}


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

    raw_data = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    # shops_raw.json は dict {"places": [...]} or 旧 list [...] 両対応
    if isinstance(raw_data, dict):
        raw = raw_data.get("places", [])
    else:
        raw = raw_data
    # Places API New 形式（id, displayName, formattedAddress, location, photos）を
    # 旧形式（place_id, name, address, lat, lng, photo_reference）に正規化
    normalized = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        if "place_id" in r:
            normalized.append(r)
            continue
        # New API 形式 → 旧形式に変換
        loc = r.get("location") or {}
        photos = r.get("photos") or []
        photo_ref = (photos[0].get("name") if photos else "") if isinstance(photos, list) else ""
        normalized.append({
            "place_id": r.get("id", ""),
            "name": (r.get("displayName") or {}).get("text", ""),
            "address": r.get("formattedAddress", ""),
            "lat": loc.get("latitude"),
            "lng": loc.get("longitude"),
            "photo_reference": photo_ref,
        })
    raw = normalized
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

            # --- STEP B: Reviews + 店舗詳細 取得 → Gemini リサーチ ---
            # （fetch_hokkaido.py 経由の候補は photo_reference を持たないので
            #   Place Details で photo_name を取った後にダウンロードする順序にする）
            reviews, place_details = fetch_reviews(places_key, pid)
            reviews_text = format_reviews(reviews)
            time.sleep(0.3)

            # --- STEP A: Photo ダウンロード ---
            # raw 由来 photo_ref を優先、無ければ Place Details 由来 photo_name にフォールバック
            image_url = ""
            effective_photo_ref = photo_ref or place_details.get("photo_name", "")
            if effective_photo_ref and usage["count"] < PHOTOS_MONTHLY_LIMIT:
                image_url = download_photo(places_key, effective_photo_ref, pid)
                if image_url:
                    usage["count"] += 1
                    save_photos_usage(usage)
                    print(f"    📷 image: {image_url}")
                time.sleep(PHOTO_SLEEP)

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

            # 「子連れOK」だけは緩い包括タグなので、設備系タグが1つもなければ弾く
            if clean["tags"] == ["子連れOK"]:
                print(f"    → SKIP: 設備系タグなし（子連れOKのみは弱根拠）")
                processed.add(pid)
                save_processed(processed)
                skipped += 1
                continue

            # evidence(クチコミ引用) に強根拠キーワードが無ければ採用しない
            # （「家族で来た」「子供と」だけの弱根拠を排除）
            if not has_strong_evidence(clean["evidence"]):
                print(f"    → SKIP: evidence に乳幼児/子連れ設備の明示記述なし")
                processed.add(pid)
                save_processed(processed)
                skipped += 1
                continue

            # --- STEP C: shops.json に追記/更新 ---
            # area は Place Details の正規化された住所優先。無ければ raw 由来。
            full_address = place_details.get("address") or address
            area = area_from_address(full_address)
            # 既存特殊エリア: 円山/宮の森（中央区の細分化）は住所キーワードで上書き
            if "宮ケ丘" in full_address or "宮の森" in full_address:
                area = "宮の森"
            elif "円山" in full_address or "南１条西２" in full_address:
                area = "円山"

            entry = {
                "place_id": pid,
                "name": name,
                "area": area,
                "genre": clean["genre"],
                "tags": clean["tags"],
                "description": clean["description"],
                "score": clean["score"],
                "lat": lat,
                "lng": lng,
                "tabelog_url": clean["tabelog_url"] or (
                    f"https://www.google.com/maps/place/?q=place_id:{pid}" if pid else ""
                ),
                "image_url": image_url or "",
                "is_chain": clean["is_chain"],
                "evidence": clean["evidence"],
                # Place Details 由来 (今後の自動化で必須)
                "address": place_details.get("address", ""),
                "rating": place_details.get("rating", 0),
                "rating_count": place_details.get("rating_count", 0),
                "hours": place_details.get("hours", []),
                "phone": place_details.get("phone", ""),
                "website": place_details.get("website", ""),
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
