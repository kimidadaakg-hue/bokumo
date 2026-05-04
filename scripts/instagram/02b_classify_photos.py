"""raw/ の写真10枚を Gemini Vision で分類し、料理3枚 + 内観2枚を選定。
出力: shop_{id}/classified.json
  {
    "food": ["raw/01.jpg", "raw/04.jpg", "raw/07.jpg"],
    "interior": ["raw/02.jpg", "raw/05.jpg"],
    "all": [{"file": "raw/01.jpg", "label": "food"}, ...]
  }
"""
import base64
import json
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "instagram"
ENV_FILE = ROOT / ".env.local"

MODEL = "gemini-2.5-flash"
PROMPT = (
    "この写真は飲食店の何の写真ですか。"
    "次のいずれか一語で答えてください: food / interior / exterior / other\n"
    "- food: 料理・ドリンク・盛り付けが主役\n"
    "- interior: 店内の客席・カウンター・装飾\n"
    "- exterior: 外観・看板・入口\n"
    "- other: 人物・メニュー表・地図など上記以外"
)


def load_env() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GEMINI_API_KEY not found in .env.local")


def classify(image_bytes: bytes, api_key: str) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent?key={api_key}")
    payload = {
        "contents": [{
            "parts": [
                {"text": PROMPT},
                {"inline_data": {"mime_type": "image/jpeg",
                                 "data": base64.b64encode(image_bytes).decode()}},
            ]
        }],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 32,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
    for label in ("food", "interior", "exterior", "other"):
        if label in text:
            return label
    return "other"


def process_shop(shop_dir: Path, api_key: str) -> None:
    raw_dir = shop_dir / "raw"
    raws = sorted(raw_dir.glob("*.jpg"))
    if len(raws) < 5:
        print(f"  写真不足({len(raws)}枚)、スキップ")
        return

    results = []
    for p in raws:
        try:
            label = classify(p.read_bytes(), api_key)
        except Exception as e:
            print(f"  分類エラー {p.name}: {e}")
            label = "other"
        results.append({"file": f"raw/{p.name}", "label": label})
        print(f"  {p.name} → {label}")
        time.sleep(0.5)  # 無料枠 RPM 配慮

    food = [r["file"] for r in results if r["label"] == "food"][:3]
    interior = [r["file"] for r in results if r["label"] == "interior"][:2]

    # 不足時のフォールバック（料理→other→interior の順で埋める）
    if len(food) < 3:
        for r in results:
            if r["file"] in food:
                continue
            if r["label"] in ("other", "exterior"):
                food.append(r["file"])
            if len(food) >= 3:
                break
    if len(interior) < 2:
        for r in results:
            if r["file"] in food or r["file"] in interior:
                continue
            interior.append(r["file"])
            if len(interior) >= 2:
                break

    out = {"food": food[:3], "interior": interior[:2], "all": results}
    (shop_dir / "classified.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  → food={len(out['food'])}, interior={len(out['interior'])}")


def main() -> None:
    today = date.today().strftime("%Y%m%d")
    day_dir = OUT_DIR / today
    selection_file = day_dir / "selected.json"
    if not selection_file.exists():
        raise SystemExit("先に 01_select_shops.py を実行してください")

    api_key = load_env()
    selected = json.loads(selection_file.read_text(encoding="utf-8"))
    for shop in selected:
        sid = shop["id"]
        shop_dir = day_dir / f"shop_{sid}"
        if not (shop_dir / "raw").exists():
            print(f"[{sid}] raw/ なし、スキップ")
            continue
        print(f"[{sid}] {shop['name']}")
        process_shop(shop_dir, api_key)


if __name__ == "__main__":
    main()
