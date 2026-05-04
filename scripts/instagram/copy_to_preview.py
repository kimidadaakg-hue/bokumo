"""今日の processed 画像 + caption を SSD プレビューフォルダにコピー。
Finderで開きやすい命名規則で配置する。
"""
import json
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOPS = ROOT / "data" / "shops.json"
OUT_DIR = ROOT / "outputs" / "instagram"
PREVIEW_ROOT = Path("/Volumes/外付けSSD/インスタ画像")


def safe_name(s: str) -> str:
    """フォルダ名に使えない文字を除去"""
    return re.sub(r"[/:\\|?*<>\"']", "", s).strip()


def main() -> None:
    today = date.today().strftime("%Y%m%d")
    today_dash = date.today().isoformat()
    day_dir = OUT_DIR / today
    selection_file = day_dir / "selected.json"
    if not selection_file.exists():
        raise SystemExit("本日の selected.json が見つかりません。先に run_daily.py を実行してください")

    if not PREVIEW_ROOT.exists():
        raise SystemExit(f"プレビュー先が見つかりません: {PREVIEW_ROOT} (SSDが接続されていない?)")

    selected = json.loads(selection_file.read_text(encoding="utf-8"))
    shops_all = {s["id"]: s for s in json.loads(SHOPS.read_text(encoding="utf-8"))}

    dest_day = PREVIEW_ROOT / today_dash
    dest_day.mkdir(parents=True, exist_ok=True)

    for i, sel in enumerate(selected, start=1):
        sid = sel["id"]
        shop = shops_all[sid]
        folder = f"{i:02d}_{safe_name(shop['name'])}_{safe_name(shop['area'])}_{safe_name(shop['genre'])}"
        dest = dest_day / folder
        dest.mkdir(exist_ok=True)
        src = day_dir / f"shop_{sid}"
        # Instagram (正方形) - フォルダ直下に配置
        for f in (src / "processed").glob("*.jpg"):
            shutil.copy2(f, dest / f.name)
        cap = src / "caption.txt"
        if cap.exists():
            shutil.copy2(cap, dest / "caption.txt")
        # TikTok (縦長) - tiktok/ サブフォルダに配置
        tt_src = src / "tiktok"
        if tt_src.exists():
            tt_dest = dest / "tiktok"
            tt_dest.mkdir(exist_ok=True)
            for f in tt_src.glob("*.jpg"):
                shutil.copy2(f, tt_dest / f.name)
            cap_tt = src / "caption_tiktok.txt"
            if cap_tt.exists():
                shutil.copy2(cap_tt, tt_dest / "caption.txt")
        print(f"  → {dest}")

    print(f"\n✅ コピー完了: {dest_day}")
    print(f"   Finderで開く: open '{dest_day}'")


if __name__ == "__main__":
    main()
