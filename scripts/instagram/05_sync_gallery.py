"""今日処理した3店舗の raw 写真を public/photos/gallery/ に同期し、
data/shops.json の gallery フィールドを更新する。

- 既存ファイルは上書き（同名で同じ内容なら無害）
- 既に gallery がある店舗は raw に新しい写真があれば差し替え
- shops.json に gallery を追加 / 更新
"""
import json
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOPS_PATH = ROOT / "data" / "shops.json"
OUT_DIR = ROOT / "outputs" / "instagram"
GALLERY_ROOT = ROOT / "public" / "photos" / "gallery"


def main() -> None:
    today = date.today().strftime("%Y%m%d")
    day_dir = OUT_DIR / today
    selection_file = day_dir / "selected.json"
    if not selection_file.exists():
        raise SystemExit("先に 01_select_shops.py を実行してください")

    selected = json.loads(selection_file.read_text(encoding="utf-8"))
    shops = json.loads(SHOPS_PATH.read_text(encoding="utf-8"))
    shops_by_id = {s["id"]: s for s in shops}

    GALLERY_ROOT.mkdir(parents=True, exist_ok=True)

    updated = 0
    for sel in selected:
        sid = sel["id"]
        if sid not in shops_by_id:
            print(f"  [{sid}] shops.json になし、スキップ")
            continue

        raw_dir = day_dir / f"shop_{sid}" / "raw"
        if not raw_dir.exists():
            print(f"  [{sid}] raw/ なし、スキップ")
            continue

        out_dir = GALLERY_ROOT / str(sid)
        out_dir.mkdir(exist_ok=True)

        urls = []
        for src in sorted(raw_dir.glob("*.jpg")):
            dest = out_dir / src.name
            shutil.copy2(src, dest)
            urls.append(f"/photos/gallery/{sid}/{src.name}")

        shops_by_id[sid]["gallery"] = urls
        updated += 1
        print(f"  [{sid}] {sel['name']}: {len(urls)} 枚")

    if updated:
        SHOPS_PATH.write_text(
            json.dumps(shops, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n✅ gallery更新: {updated} 店")
        print("   ⚠️  data/shops.json と public/photos/gallery/ が変更されました。")
        print("       サイトに反映するには git commit + push が必要です。")
    else:
        print("更新なし")


if __name__ == "__main__":
    main()
