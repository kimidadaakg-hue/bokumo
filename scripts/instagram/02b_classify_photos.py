"""raw/ の写真10枚を Gemini Vision で分類し、料理3枚 + 内観2枚を選定。

「お子様メニュー」と判定された料理は food リストの先頭に並べるので、
04_render_overlays.py 側で自動的にメインカット（slide_plain）に採用される。

出力: shop_{id}/classified.json
  {
    "kids_menu": ["raw/03.jpg"],
    "food": ["raw/03.jpg", "raw/01.jpg", "raw/04.jpg"],   # kids_menu 含む
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
    "次のいずれか一語で答えてください: kids_menu / food / interior / exterior / other\n"
    "- kids_menu: 明らかに子供向けの料理。"
    "旗(ピック)が立った日の丸プレート、星型・ハート型・動物型の盛り付け、"
    "「お子様」「キッズ」と書かれた食器・ランチョンマット・トレー、"
    "ハンバーグ＋エビフライ＋ポテト＋ご飯のような典型的なお子様ランチセット、"
    "小さい器に盛られた取り分けプレートなど。\n"
    "  ※ ただの唐揚げ、普通サイズのハンバーグ、カレー、ラーメン等の"
    "「大人も食べる料理」は kids_menu ではなく food とする。\n"
    "- food: 上記以外の料理・ドリンク・盛り付けが主役（一般向け）\n"
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
    # kids_menu を最優先で判定（"food" は "kids_menu" の応答にも含まれうるため先に）
    for label in ("kids_menu", "food", "interior", "exterior", "other"):
        if label in text:
            return label
    # フォールバック: Gemini が和訳で返したケースを救う
    if any(k in text for k in ("キッズ", "お子様", "子供", "kids")):
        return "kids_menu"
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

    kids_menu = [r["file"] for r in results if r["label"] == "kids_menu"]
    food_only = [r["file"] for r in results if r["label"] == "food"]
    interior = [r["file"] for r in results if r["label"] == "interior"][:2]

    # food リストは「お子様メニュー優先」で詰める
    food = (kids_menu + food_only)[:3]

    # 不足時のフォールバック（other / exterior で埋める）
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

    out = {
        "kids_menu": kids_menu,
        "food": food[:3],
        "interior": interior[:2],
        "all": results,
    }
    (shop_dir / "classified.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    kids_mark = f" (kids_menu={len(kids_menu)})" if kids_menu else ""
    print(f"  → food={len(out['food'])}, interior={len(out['interior'])}{kids_mark}")


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
