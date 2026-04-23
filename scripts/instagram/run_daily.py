"""日次バッチ: 01〜04 を順に実行する。
Claude Code 側の処理はここで完結し、
このあと Claude in Chrome が AI Studio + Instagram を操作する。
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [
    "01_select_shops.py",
    "02_fetch_photos.py",
    "03_generate_caption.py",
    "04_render_overlays.py",
]


def main() -> None:
    for step in STEPS:
        print(f"\n=== {step} ===")
        r = subprocess.run([sys.executable, str(HERE / step)])
        if r.returncode != 0:
            print(f"!! {step} 失敗 (exit {r.returncode})")
            sys.exit(r.returncode)
    print("\n✅ 完了。outputs/instagram/YYYYMMDD/shop_*/processed/ に画像5枚 × 3店舗。")
    print("   caption.txt をコピペしてスマホからInstagramに投稿してください。")
    print("   投稿が終わったら: python3 scripts/instagram/mark_posted.py")


if __name__ == "__main__":
    main()
