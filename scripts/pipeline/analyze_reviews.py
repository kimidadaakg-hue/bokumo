#!/usr/bin/env python3
"""
analyze_reviews.py - Gemini でクチコミから子連れ対応情報を抽出する。

Places + Gemini クチコミ方式（方式②）

Input:  scripts/pipeline/details.json (reviews 付き)
Output: scripts/pipeline/kid_friendly.json
Resume: scripts/pipeline/analyze_progress.json
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
IN_PATH = SCRIPT_DIR / "details.json"
OUT_PATH = SCRIPT_DIR / "kid_friendly.json"
PROGRESS_PATH = SCRIPT_DIR / "analyze_progress.json"

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

SLEEP_SEC = 4.5
DAILY_LIMIT = 1000

STRICT_PROMPT = """あなたは子連れ飲食店情報のリサーチャーです。
以下は「{name}」のGoogleマップの実際のクチコミです。

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

利用可能タグ (クチコミに確実な記載がある場合のみ使用):
- 個室あり        : 「個室/半個室/貸切」等の明示的記述がある場合のみ
- 座敷あり        : 「座敷/小上がり/畳/掘りごたつ」等の明示的記述がある場合のみ
- キッズチェアあり  : 「キッズチェア/子供用椅子/ベビーチェア/ハイチェア」等の明示的記述がある場合のみ
- 子供メニューあり  : 「お子様メニュー/キッズメニュー/子供用の〇〇」等の明示的記述がある場合のみ
- ベビーカーOK     : 「ベビーカー入店可/ベビーカーOK」等の明示的記述がある場合のみ
- 子連れOK        : 「子連れ歓迎/お子様連れ/家族連れ/子供と一緒」等、子連れ来店の実績や歓迎の記述がある場合

scoreの基準:
- 5: 子連れ歓迎が明確+複数の子連れ対応設備の記述あり
- 4: 子連れ対応設備の明示的言及あり、またはお子様連れの来店実績が複数クチコミで確認
- 3: 子連れの言及なし(デフォルト)
- 2: 大人向け/静か/子連れは難しそう等の記述あり
- 1: 子連れ不可/非推奨の明示あり

クチコミに子連れ情報が全くない場合: tags=[], score=3, evidence=[], descriptionは店の一般的特徴のみ。
JSONのみ返答。コードブロック禁止。
"""

VALID_TAGS = {
    "個室あり", "座敷あり", "キッズチェアあり",
    "子供メニューあり", "ベビーカーOK", "子連れOK",
}


def load_json(path, default=None):
    if not path.exists():
        return default if default is not None else []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else []


def save_json(path, data):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, str(path))


def format_reviews(reviews):
    if not reviews:
        return ""
    lines = []
    for i, r in enumerate(reviews[:5], 1):
        text = r.get("text", "").replace("\n", " ").strip()
        if len(text) > 500:
            text = text[:500] + "…"
        rating = r.get("rating", "?")
        if text:
            lines.append(f"[{i}] ★{rating} {text}")
    return "\n".join(lines) if lines else ""


def extract_json_from_text(text):
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


def call_gemini(api_key, name, reviews_text):
    prompt = STRICT_PROMPT.format(name=name, reviews=reviews_text)
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    req = urllib.request.Request(
        f"{GEMINI_ENDPOINT}?key={api_key}",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            payload = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        if e.code == 429:
            raise  # 呼び出し元で処理
        print(f"    [Gemini {e.code}] {body_err[:150]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"    [Gemini err] {e}", file=sys.stderr)
        return None

    try:
        parts = payload["candidates"][0]["content"]["parts"]
        text = "\n".join(p.get("text", "") for p in parts if "text" in p)
    except Exception:
        return None
    return extract_json_from_text(text)


def sanitize(result):
    tags = [t for t in (result.get("tags") or []) if isinstance(t, str) and t in VALID_TAGS]
    tags = list(dict.fromkeys(tags))

    try:
        score = int(result.get("score", 3))
    except Exception:
        score = 3
    score = max(1, min(5, score))

    desc = result.get("description") or ""
    if not isinstance(desc, str):
        desc = ""
    if len(desc) > 80:
        desc = desc[:80]

    evidence = [str(x)[:120] for x in (result.get("evidence") or []) if x]

    return {"tags": tags, "score": score, "description": desc, "evidence": evidence}


def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY 未設定", file=sys.stderr)
        sys.exit(1)

    details = load_json(IN_PATH, [])
    if not details:
        print(f"ERROR: {IN_PATH} が見つからないか空です", file=sys.stderr)
        sys.exit(1)

    processed = set(load_json(PROGRESS_PATH, []))
    kid_friendly = load_json(OUT_PATH, [])
    existing_ids = {s.get("place_id") for s in kid_friendly}

    print("=" * 60)
    print("BOKUMO analyze_reviews.py (Places + Gemini クチコミ方式)")
    print("=" * 60)
    print(f"対象: {len(details)} 件 / 処理済み: {len(processed)} 件")
    print(f"モデル: {GEMINI_MODEL}")
    print()

    gemini_count = 0
    ok = 0
    no_review = 0
    failed = 0
    quota_hit = False

    try:
        for i, d in enumerate(details, 1):
            pid = d.get("place_id", "")
            name = d.get("name", "")

            if pid in processed:
                continue

            reviews = d.get("reviews") or []
            if not reviews:
                print(f"[{i}/{len(details)}] {name} → クチコミなし(skip)")
                processed.add(pid)
                no_review += 1
                continue

            reviews_text = format_reviews(reviews)

            print(f"[{i}/{len(details)}] {name}", end="", flush=True)

            if gemini_count >= DAILY_LIMIT:
                print(f" ⚠️ 日次上限{DAILY_LIMIT}件到達。中断。")
                quota_hit = True
                break

            try:
                result = call_gemini(api_key, name, reviews_text)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f" ⚠️ Gemini 429。中断 → 再実行で続きから。")
                    quota_hit = True
                    break
                raise

            gemini_count += 1

            if not result:
                print(" → 解析失敗")
                failed += 1
                processed.add(pid)
                time.sleep(SLEEP_SEC)
                continue

            clean = sanitize(result)
            processed.add(pid)

            # kid_friendly に追加（score >= 3 かつ tags 非空、またはscore >= 4）
            entry = {**d, **clean}
            entry.pop("reviews", None)  # reviews は重いので除去

            if pid not in existing_ids:
                kid_friendly.append(entry)
                existing_ids.add(pid)

            ok += 1
            tag_str = "/".join(clean["tags"]) if clean["tags"] else "タグなし"
            print(f" → [★{clean['score']}] {tag_str}")

            # 保存（50件ごと）
            if ok % 50 == 0:
                save_json(OUT_PATH, kid_friendly)
                save_json(PROGRESS_PATH, sorted(processed))
                print(f"    [保存: {ok}件, Gemini使用: {gemini_count}]")

            time.sleep(SLEEP_SEC)

    except KeyboardInterrupt:
        print("\n中断")

    # 最終保存
    save_json(OUT_PATH, kid_friendly)
    save_json(PROGRESS_PATH, sorted(processed))

    print()
    print("=" * 60)
    print(f"{'中断' if quota_hit else '完了'}")
    print(f"  解析成功: {ok}")
    print(f"  クチコミなし: {no_review}")
    print(f"  解析失敗: {failed}")
    print(f"  Gemini使用: {gemini_count}")
    print(f"  kid_friendly.json: {len(kid_friendly)} 件")
    print(f"  出力: {OUT_PATH}")
    if quota_hit:
        print("  → 再実行すれば続きから処理します。")
    print("=" * 60)


if __name__ == "__main__":
    main()
