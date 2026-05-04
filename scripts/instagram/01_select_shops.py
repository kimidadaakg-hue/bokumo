"""本日投稿する3店舗を選定する。
- posted_history.json に記録済みの shop_id は除外
- タグ数とスコアで優先度を計算し、上位プールからランダム選択
  優先度 = タグ数 × 3 + スコア
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
TOP_POOL_SIZE = 30  # 上位30店からランダム3つ選ぶ


def priority(s: dict) -> int:
    """タグ数を重視 + スコアでブースト"""
    return len(s.get("tags", [])) * 3 + s.get("score", 0)


def main() -> None:
    shops = json.loads(SHOPS.read_text(encoding="utf-8"))
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    posted = set(history.get("posted_shop_ids", []))

    candidates = [
        s for s in shops
        if s["id"] not in posted and s.get("place_id")
    ]
    if len(candidates) < DAILY_COUNT:
        raise SystemExit(f"投稿可能な店舗が不足: {len(candidates)}店舗")

    # 優先度降順でソート → 上位プールから当日シードでランダム3つ
    candidates.sort(key=priority, reverse=True)
    pool_size = min(TOP_POOL_SIZE, len(candidates))
    pool = candidates[:pool_size]

    random.seed(date.today().isoformat())
    picked = random.sample(pool, DAILY_COUNT)

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
    print(f"選定完了: {today} (上位{pool_size}店プールから)")
    for s in picked:
        print(f"  - [{s['id']}] {s['name']} ({s['area']}/{s['genre']}) "
              f"tags={len(s.get('tags', []))} score={s.get('score', 0)} prio={priority(s)}")
    print(f"出力: {selection}")


if __name__ == "__main__":
    main()
