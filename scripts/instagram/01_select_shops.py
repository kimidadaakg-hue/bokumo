"""本日投稿する3店舗を選定する。
- posted_history.json に記録済みの shop_id は除外
- 高評価(score>=4) を優先
- ランダムで3店舗ピック
"""
import json
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOPS = ROOT / "data" / "shops.json"
HISTORY = ROOT / "logs" / "posted_history.json"
OUT_DIR = ROOT / "outputs" / "instagram"

DAILY_COUNT = 3


def main() -> None:
    shops = json.loads(SHOPS.read_text(encoding="utf-8"))
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    posted = set(history.get("posted_shop_ids", []))

    candidates = [
        s for s in shops
        if s["id"] not in posted
        and s.get("score", 0) >= 4
        and s.get("place_id")
    ]
    if len(candidates) < DAILY_COUNT:
        candidates = [s for s in shops if s["id"] not in posted and s.get("place_id")]

    if len(candidates) < DAILY_COUNT:
        raise SystemExit(f"投稿可能な店舗が不足: {len(candidates)}店舗")

    random.seed(date.today().isoformat())
    picked = random.sample(candidates, DAILY_COUNT)

    today = date.today().strftime("%Y%m%d")
    day_dir = OUT_DIR / today
    day_dir.mkdir(parents=True, exist_ok=True)
    selection = day_dir / "selected.json"
    selection.write_text(
        json.dumps([{"id": s["id"], "name": s["name"], "place_id": s["place_id"],
                     "area": s["area"], "genre": s["genre"], "tags": s["tags"],
                     "score": s["score"]} for s in picked],
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"選定完了: {today}")
    for s in picked:
        print(f"  - [{s['id']}] {s['name']} ({s['area']}/{s['genre']})")
    print(f"出力: {selection}")


if __name__ == "__main__":
    main()
