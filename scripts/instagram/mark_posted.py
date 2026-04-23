"""本日選定した3店舗を posted_history.json に追記する。
Instagram への下書き登録が完了したら手動で実行する。
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "instagram"
HISTORY = ROOT / "logs" / "posted_history.json"


def main() -> None:
    today = date.today().strftime("%Y%m%d")
    selection_file = OUT_DIR / today / "selected.json"
    if not selection_file.exists():
        raise SystemExit("本日の selected.json が見つかりません")

    selected = json.loads(selection_file.read_text(encoding="utf-8"))
    history = json.loads(HISTORY.read_text(encoding="utf-8"))

    posted = set(history.get("posted_shop_ids", []))
    added = []
    for s in selected:
        if s["id"] not in posted:
            posted.add(s["id"])
            added.append(s["id"])

    history["posted_shop_ids"] = sorted(posted)
    history["last_updated"] = date.today().isoformat()
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"追加: {added}")
    print(f"累計投稿済み: {len(posted)} / 559店舗")


if __name__ == "__main__":
    main()
