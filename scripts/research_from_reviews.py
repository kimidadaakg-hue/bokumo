"""
Google Maps のクチコミ(Place Details Enterprise SKU)を取得し、
Gemini 2.5 Flash-Lite に「クチコミから読み取れる情報だけ」で
子連れ対応情報を抽出させる。推測禁止・根拠(evidence)必須。

使い方:
    export GOOGLE_PLACES_API_KEY="AIza..."
    export GEMINI_API_KEY="AIza..."
    python3 scripts/research_from_reviews.py

出力:
    data/shops.json の各店舗に
      - tags / score / description を更新
      - evidence (クチコミ引用) を追加
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

ROOT = Path(__file__).resolve().parent.parent
SHOPS_PATH = ROOT / "data" / "shops.json"

PLACES_FIELDS = ",".join(["id", "displayName", "reviews", "primaryType"])
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

SLEEP_SEC = 10.0
MAX_REVIEWS = 5


STRICT_PROMPT = """あなたは子連れ飲食店情報のリサーチャーです。
以下は「{name}」のGoogleマップのクチコミ(実際のユーザー投稿)です。

【クチコミ】
{reviews}

このクチコミ**のみ**を根拠に、以下のJSONを返してください。
クチコミに明示的な記述がないタグは絶対に含めないでください。推測・一般常識での補完は禁止です。

返却フォーマット:
{{
  "tags": ["該当タグのみの配列"],
  "score": 1から5の整数,
  "description": "クチコミから読み取れる事実だけで書いた子連れ目線の紹介文(50文字以内)",
  "evidence": ["根拠になったクチコミの短い引用(30文字程度)の配列"]
}}

利用可能タグ (必ず以下の文字列のいずれか・部分一致不可):
- ベビーカーOK      : 「ベビーカーで入れた/入店可」等の明示的記述
- 座敷あり         : 「座敷/小上がり/畳/掘りごたつ」等の明示的記述
- キッズチェアあり  : 「キッズチェア/子供用椅子/ハイチェア/ベビーチェア」等の記述
- 個室あり         : 「個室/半個室/貸切可」等の記述
- 騒いでもOK       : 「子連れ歓迎/赤ちゃんOK/騒いでも大丈夫」等の記述
- 子供メニューあり  : 「お子様メニュー/キッズメニュー/子供用の○○」等の記述

scoreの基準:
- 5: 子連れ歓迎が明確+複数の装備あり
- 4: 少なくとも1つの子連れ装備の明示的言及あり
- 3: 子連れの言及なし(デフォルト)
- 2: 大人向け/静か/子連れは難しそう等の記述あり
- 1: 子連れ不可/非推奨の明示あり

クチコミに子連れ情報が全くない場合:
  tags=[], score=3, evidence=[], description=店の一般的特徴(クチコミから読めることのみ)

返答はJSONのみ。コードブロック禁止。説明文禁止。
"""


def load_keys() -> tuple[str, str]:
    places = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    gemini = os.environ.get("GEMINI_API_KEY", "").strip()
    if not places or not gemini:
        print(
            "ERROR: GOOGLE_PLACES_API_KEY と GEMINI_API_KEY の両方を設定してください。",
            file=sys.stderr,
        )
        sys.exit(1)
    return places, gemini


def fetch_reviews(places_key: str, place_id: str) -> list[dict[str, Any]]:
    url = f"https://places.googleapis.com/v1/places/{place_id}?languageCode=ja&regionCode=JP"
    req = request.Request(
        url,
        method="GET",
        headers={
            "X-Goog-Api-Key": places_key,
            "X-Goog-FieldMask": PLACES_FIELDS,
        },
    )
    try:
        with request.urlopen(req, timeout=20) as res:
            payload = json.loads(res.read().decode("utf-8"))
            return payload.get("reviews", []) or []
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"   [Places {e.code}] {body[:200]}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"   [Places err] {e}", file=sys.stderr)
        return []


def format_reviews(reviews: list[dict[str, Any]]) -> str:
    lines = []
    for i, r in enumerate(reviews[:MAX_REVIEWS], 1):
        text = (r.get("originalText") or r.get("text") or {}).get("text", "")
        if not text:
            continue
        rating = r.get("rating", "?")
        ptime = r.get("relativePublishTimeDescription", "")
        # 改行を整える
        text = text.replace("\n", " ").strip()
        if len(text) > 500:
            text = text[:500] + "…"
        lines.append(f"[{i}] ★{rating} ({ptime}) {text}")
    return "\n".join(lines) if lines else "(クチコミ無し)"


def extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    s = text.find("{")
    e = text.rfind("}")
    if s == -1 or e == -1 or e < s:
        return None
    try:
        return json.loads(text[s : e + 1])
    except Exception:
        return None


def gemini_analyze(
    gemini_key: str, name: str, reviews_text: str
) -> dict[str, Any] | None:
    prompt = STRICT_PROMPT.format(name=name, reviews=reviews_text)
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    req = request.Request(
        f"{GEMINI_ENDPOINT}?key={gemini_key}",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=60) as res:
            payload = json.loads(res.read().decode("utf-8"))
    except error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        print(f"   [Gemini {e.code}] {body_err[:200]}", file=sys.stderr)
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


VALID_TAGS = {
    "ベビーカーOK",
    "座敷あり",
    "キッズチェアあり",
    "個室あり",
    "騒いでもOK",
    "子供メニューあり",
}


def sanitize(res: dict[str, Any]) -> dict[str, Any]:
    tags = res.get("tags") or []
    tags = [t for t in tags if isinstance(t, str) and t in VALID_TAGS]
    # 重複排除しつつ順序維持
    tags = list(dict.fromkeys(tags))

    score = res.get("score", 3)
    try:
        score = int(score)
    except Exception:
        score = 3
    score = max(1, min(5, score))

    desc = res.get("description") or ""
    if not isinstance(desc, str):
        desc = ""
    if len(desc) > 80:
        desc = desc[:80]

    evidence = res.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = []
    evidence = [str(x)[:120] for x in evidence if x]

    return {
        "tags": tags,
        "score": score,
        "description": desc,
        "evidence": evidence,
    }


def main() -> None:
    places_key, gemini_key = load_keys()
    shops = json.loads(SHOPS_PATH.read_text(encoding="utf-8"))
    print(f"対象: {len(shops)} 店舗")
    print()

    ok = 0
    no_review = 0
    failed = 0

    for i, s in enumerate(shops, 1):
        name = s.get("name", "")
        pid = s.get("place_id")
        print(f"[{i}/{len(shops)}] {name}")
        if not pid:
            print("   SKIP: place_idなし")
            continue
        # 再開: evidence 済みはスキップ
        if "evidence" in s and isinstance(s.get("evidence"), list):
            print("   SKIP: 解析済み(evidence有り)")
            ok += 1
            continue

        reviews = fetch_reviews(places_key, pid)
        if not reviews:
            print("   クチコミが取得できなかったので既存データを維持")
            no_review += 1
            time.sleep(1.0)
            continue

        print(f"   クチコミ取得: {len(reviews)} 件")
        reviews_text = format_reviews(reviews)

        result = gemini_analyze(gemini_key, name, reviews_text)
        if not result:
            print("   Gemini 解析失敗")
            failed += 1
            time.sleep(SLEEP_SEC)
            continue

        clean = sanitize(result)

        # 更新
        s["tags"] = clean["tags"]
        s["score"] = clean["score"]
        s["description"] = clean["description"] or s.get("description", "")
        s["evidence"] = clean["evidence"]

        ok += 1
        tag_str = "/".join(clean["tags"]) if clean["tags"] else "タグなし"
        print(f"   → [★{clean['score']}] {tag_str}")
        print(f"     {clean['description']}")
        if clean["evidence"]:
            for ev in clean["evidence"]:
                print(f"     ▸ {ev}")

        # 1件ごとに保存(中断耐性)
        SHOPS_PATH.write_text(
            json.dumps(shops, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        time.sleep(SLEEP_SEC)

    print()
    print(f"=== 完了 ===")
    print(f"  解析成功: {ok} 件")
    print(f"  クチコミなし: {no_review} 件")
    print(f"  Gemini失敗: {failed} 件")
    print(f"  保存: {SHOPS_PATH}")


if __name__ == "__main__":
    main()
