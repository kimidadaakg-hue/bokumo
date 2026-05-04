"""投稿済み店舗を posted_history.json に追記する。

使い方:
  # 本日選定した3店舗ぜんぶ記録（投稿が3件全部済んだ時）
  python3 mark_posted.py

  # 特定の店舗だけ記録（例: shop_20 と shop_167 だけ投稿した時）
  python3 mark_posted.py 20 167
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "instagram"
HISTORY = ROOT / "logs" / "posted_history.json"


def main() -> None:
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    posted = set(history.get("posted_shop_ids", []))

    # 引数があればそのIDだけ、無ければ本日の selected.json 全部
    if len(sys.argv) > 1:
        try:
            target_ids = [int(x) for x in sys.argv[1:]]
        except ValueError:
            raise SystemExit("引数は店舗ID(数字)のみ指定可能。例: python3 mark_posted.py 20 167")
        print(f"指定された店舗: {target_ids}")
    else:
        today = date.today().strftime("%Y%m%d")
        selection_file = OUT_DIR / today / "selected.json"
        if not selection_file.exists():
            raise SystemExit("本日の selected.json が見つかりません")
        selected = json.loads(selection_file.read_text(encoding="utf-8"))
        target_ids = [s["id"] for s in selected]
        print(f"本日選定の3店舗ぜんぶ記録: {target_ids}")

    added = []
    for sid in target_ids:
        if sid not in posted:
            posted.add(sid)
            added.append(sid)

    history["posted_shop_ids"] = sorted(posted)
    history["last_updated"] = date.today().isoformat()
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"追加: {added}")
    print(f"累計投稿済み: {len(posted)} / 559店舗")


if __name__ == "__main__":
    main()
