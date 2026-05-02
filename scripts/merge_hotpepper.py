"""scripts/hotpepper_fetched.json の店舗を data/shops.json にマージする。

- ホットペッパーの店舗ID（hotpepper_url 内の strJxxxxxxx）で重複チェック
- name+area の組み合わせでも軽く重複チェック（フォールバック）
- 既存の最大IDの次から新IDを付与して追記
- 上書きはしない（既存559店は保護）
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOPS_PATH = ROOT / "data" / "shops.json"
FETCHED_PATH = Path(__file__).resolve().parent / "hotpepper_fetched.json"


def hp_id_from_url(url: str | None) -> str | None:
    """hotpepper_url から strJxxxxxxx を抽出"""
    if not url:
        return None
    m = re.search(r"strJ\d+", url)
    return m.group(0) if m else None


def main() -> None:
    if not FETCHED_PATH.exists():
        raise SystemExit(f"先に get_shops_hotpepper.py を実行してください: {FETCHED_PATH}")

    existing = json.loads(SHOPS_PATH.read_text(encoding="utf-8"))
    fetched = json.loads(FETCHED_PATH.read_text(encoding="utf-8"))
    print(f"既存: {len(existing)} 店 / フェッチ済: {len(fetched)} 店")

    # 既存の重複チェックキー
    existing_hp_ids = {hp_id_from_url(s.get("hotpepper_url")) for s in existing}
    existing_hp_ids.discard(None)
    existing_name_area = {(s["name"], s["area"]) for s in existing}

    next_id = max(s["id"] for s in existing) + 1 if existing else 1

    new_shops = []
    dup_hp = 0
    dup_name = 0
    for s in fetched:
        hp_id = hp_id_from_url(s.get("hotpepper_url"))
        if hp_id and hp_id in existing_hp_ids:
            dup_hp += 1
            continue
        if (s["name"], s["area"]) in existing_name_area:
            dup_name += 1
            continue
        s = dict(s)
        s["id"] = next_id
        next_id += 1
        new_shops.append(s)

    print(f"重複(hp_id一致): {dup_hp} 件")
    print(f"重複(name+area一致): {dup_name} 件")
    print(f"新規追加対象: {len(new_shops)} 件")

    if not new_shops:
        print("追加なし")
        return

    if "--dry-run" in sys.argv:
        print("[DRY RUN] 書き込みません")
        for s in new_shops[:10]:
            print(f"  + [{s['id']}] {s['name']} ({s['area']}/{s['genre']}) tags={s.get('tags')}")
        if len(new_shops) > 10:
            print(f"  ... 他{len(new_shops) - 10}件")
        return

    merged = existing + new_shops
    SHOPS_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ data/shops.json に追記: 合計 {len(merged)} 店")


if __name__ == "__main__":
    main()
