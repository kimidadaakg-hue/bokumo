"""今日生成した TikTok 画像 + caption を iCloud Drive にコピー（iPhone から取得用）。

外付けSSDから直接 AirDrop すると macOS の sharingd デーモンが
日本語パス + 深い階層で path 解決に失敗するため、iCloud Drive 経由で
iPhone のファイルアプリから取得できるようにする。

iPhone 側操作:
  ファイル.app → iCloud Drive → bokumo_tiktok → {YYYYMMDD} → {店ID}_{店名}/
  → 6枚を選択して TikTok アプリで「写真」モード投稿

容量管理: 7日以上前のディレクトリは自動削除。
"""
import json
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "instagram"
ICLOUD = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "bokumo_tiktok"
KEEP_DAYS = 7


def safe_name(name: str) -> str:
    """ファイルシステム安全な名前に変換."""
    return re.sub(r'[/\\:*?"<>|]', '_', name)[:50]


def main() -> None:
    today = date.today().strftime("%Y%m%d")
    src_day_dir = OUT_DIR / today
    selection_file = src_day_dir / "selected.json"
    if not selection_file.exists():
        print(f"❌ 本日の selected.json なし: {selection_file}")
        return

    selected = json.loads(selection_file.read_text(encoding="utf-8"))
    dst_day_dir = ICLOUD / today
    dst_day_dir.mkdir(parents=True, exist_ok=True)

    print(f"iCloud Drive へコピー: {dst_day_dir}")
    for s in selected:
        sid = s["id"]
        name = s["name"]
        src_shop_dir = src_day_dir / f"shop_{sid}"
        src_tiktok_dir = src_shop_dir / "tiktok"
        if not src_tiktok_dir.exists():
            print(f"  [{sid}] {name}: tiktok/ なし、スキップ")
            continue

        dst_shop_dir = dst_day_dir / f"{sid:04d}_{safe_name(name)}"
        dst_shop_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        for img in sorted(src_tiktok_dir.glob("*.jpg")):
            shutil.copy2(img, dst_shop_dir / img.name)
            copied += 1

        # caption も一緒にコピー（iPhone で貼り付け用）
        caption_src = src_shop_dir / "caption_tiktok.txt"
        if caption_src.exists():
            shutil.copy2(caption_src, dst_shop_dir / "caption.txt")

        print(f"  [{sid}] {name}: {copied}枚 + caption → {dst_shop_dir.name}")

    # 容量管理: KEEP_DAYS より古いディレクトリは削除
    cleaned = 0
    for old_dir in ICLOUD.iterdir():
        if not old_dir.is_dir() or not re.match(r'^\d{8}$', old_dir.name):
            continue
        try:
            old_date = date(int(old_dir.name[:4]), int(old_dir.name[4:6]), int(old_dir.name[6:8]))
            days_old = (date.today() - old_date).days
            if days_old > KEEP_DAYS:
                shutil.rmtree(old_dir)
                cleaned += 1
                print(f"  古い分削除: {old_dir.name} ({days_old}日前)")
        except (ValueError, OSError) as e:
            print(f"  削除失敗 {old_dir.name}: {e}")

    if cleaned:
        print(f"古いディレクトリ削除: {cleaned} 件")
    print(f"\n✅ iPhone のファイルアプリで以下を開けます:")
    print(f"   iCloud Drive → bokumo_tiktok → {today}")


if __name__ == "__main__":
    main()
