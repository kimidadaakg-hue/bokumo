"""
details_central.json の各店舗についてクチコミを取得し、
Gemini 2.5 Flash に厳格プロンプトで子連れ対応情報を抽出させる。

出力: scripts/analyzed_central.json (再開可能)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

SCRIPT_DIR = Path(__file__).resolve().parent
IN_PATH = SCRIPT_DIR / "details_central.json"
OUT_PATH = SCRIPT_DIR / "analyzed_central.json"

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

PLACES_FIELD_MASK = "id,displayName,reviews"

SLEEP_SEC = 2.5
MAX_REVIEWS = 5

STRICT_PROMPT = """あなたは子連れ飲食店情報のリサーチャーです。
以下は「{name}」のGoogleマップのクチコミ(実際のユーザー投稿)です。

【クチコミ】
{reviews}

このクチコミ**のみ**を根拠に、以下のJSONを返してください。
クチコミに明示的な記述がないタグは絶対に含めないでください。推測禁止。

{{
  "tags": ["該当タグのみ"],
  "score": 1-5の整数,
  "description": "クチコミから読み取れる事実だけで50文字以内の紹介",
  "evidence": ["根拠のクチコミ引用(30文字前後)の配列"]
}}

利用可能タグ:
- ベビーカーOK
- 座敷あり
- キッズチェアあり
- 個室あり
- 騒いでもOK
- 子供メニューあり

scoreの基準:
- 5: 子連れ歓迎が明確+複数の子連れ装備あり
- 4: 子連れ装備の明示的言及あり / お子様連れの来店が複数クチコミで確認
- 3: 子連れの言及なし(デフォルト)
- 2: 大人向け/静か/子連れは難しそう
- 1: 子連れ不可/非推奨の明示あり

クチコミに子連れ情報が全くない場合: tags=[], score=3, evidence=[], descriptionは店の一般的特徴のみ。
JSONのみ返答。コードブロック禁止。
"""

VALID_TAGS = {
    "ベビーカーOK", "座敷あり", "キッズチェアあり",
    "個室あり", "騒いでもOK", "子供メニューあり",
}


def fetch_reviews(key: str, pid: str) -> list[dict]:
    url = f"https://places.googleapis.com/v1/places/{pid}?languageCode=ja&regionCode=JP"
    req = request.Request(
        url, method="GET",
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": PLACES_FIELD_MASK},
    )
    try:
        with request.urlopen(req, timeout=20) as res:
            payload = json.loads(res.read().decode("utf-8"))
            return payload.get("reviews", []) or []
    except Exception as e:
        print(f"   [Places err] {e}", file=sys.stderr)
        return []


def format_reviews(reviews: list[dict]) -> str:
    lines = []
    for i, r in enumerate(reviews[:MAX_REVIEWS], 1):
        text = (r.get("originalText") or r.get("text") or {}).get("text", "")
        if not text:
            continue
        rating = r.get("rating", "?")
        text = text.replace("\n", " ").strip()
        if len(text) > 500:
            text = text[:500] + "…"
        lines.append(f"[{i}] ★{rating} {text}")
    return "\n".join(lines) if lines else ""


def extract_json(text: str) -> dict | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    s = text.find("{")
    e = text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        return json.loads(text[s:e + 1])
    except Exception:
        return None


def gemini(key: str, name: str, reviews_text: str) -> dict | None:
    prompt = STRICT_PROMPT.format(name=name, reviews=reviews_text)
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    req = request.Request(
        f"{GEMINI_ENDPOINT}?key={key}",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=60) as res:
            payload = json.loads(res.read().decode("utf-8"))
    except error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        print(f"   [Gemini {e.code}] {body_err[:150]}", file=sys.stderr)
        if e.code == 429:
            raise
        return None
    except Exception as e:
        print(f"   [Gemini err] {e}", file=sys.stderr)
        return None

    try:
        parts = payload["candidates"][0]["content"]["parts"]
        text = "\n".join(p.get("text", "") for p in parts if "text" in p)
    except Exception:
        return None
    return extract_json(text)


def sanitize(r: dict) -> dict:
    tags = [t for t in (r.get("tags") or []) if isinstance(t, str) and t in VALID_TAGS]
    tags = list(dict.fromkeys(tags))
    try:
        score = int(r.get("score", 3))
    except Exception:
        score = 3
    score = max(1, min(5, score))
    desc = r.get("description") or ""
    if not isinstance(desc, str):
        desc = ""
    if len(desc) > 80:
        desc = desc[:80]
    ev = [str(x)[:120] for x in (r.get("evidence") or []) if x]
    return {"tags": tags, "score": score, "description": desc, "evidence": ev}


def main() -> None:
    places_key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not places_key or not gemini_key:
        print("ERROR: keys missing", file=sys.stderr)
        sys.exit(1)

    details = json.loads(IN_PATH.read_text(encoding="utf-8"))
    # 既存結果 (再開用)
    if OUT_PATH.exists():
        existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        done_ids = {e["place_id"] for e in existing if "place_id" in e}
        analyzed = list(existing)
        print(f"再開: 既に {len(done_ids)} 件解析済み")
    else:
        done_ids = set()
        analyzed = []

    print(f"対象: {len(details)} 件")
    print()

    quota_hit = False
    for i, d in enumerate(details, 1):
        pid = d["place_id"]
        name = d["name"]
        if pid in done_ids:
            print(f"[{i}/{len(details)}] SKIP(済): {name}")
            continue

        print(f"[{i}/{len(details)}] {name}")
        reviews = fetch_reviews(places_key, pid)
        if not reviews:
            print("   クチコミ無し/取得失敗 → tags空で記録")
            analyzed.append({
                **d,
                "tags": [],
                "score": 3,
                "description": "",
                "evidence": [],
                "_no_reviews": True,
            })
            time.sleep(0.3)
            continue

        reviews_text = format_reviews(reviews)
        try:
            result = gemini(gemini_key, name, reviews_text)
        except error.HTTPError as e:
            if e.code == 429:
                print(f"   ⚠️  Gemini 429 (クォータ枯渇)。中断 → 翌日 --resume で続行可")
                quota_hit = True
                break
            raise

        if not result:
            print("   Gemini解析失敗 → スキップ(再実行で retry)")
            time.sleep(SLEEP_SEC)
            continue

        clean = sanitize(result)
        analyzed.append({**d, **clean})

        # 進捗保存
        OUT_PATH.write_text(
            json.dumps(analyzed, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        tag_str = "/".join(clean["tags"]) if clean["tags"] else "タグなし"
        print(f"   → [★{clean['score']}] {tag_str} | {clean['description'][:40]}")
        time.sleep(SLEEP_SEC)

    # 保存
    OUT_PATH.write_text(
        json.dumps(analyzed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"=== {'中断' if quota_hit else '完了'} ===")
    print(f"解析済み: {len(analyzed)} / {len(details)} 件")
    print(f"出力: {OUT_PATH}")
    if quota_hit:
        print("翌日に同じコマンドで再実行すれば続きから処理します。")


if __name__ == "__main__":
    main()
