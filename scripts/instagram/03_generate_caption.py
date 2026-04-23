"""各店舗のInstagramキャプションとハッシュタグを生成する。
- 店舗データ + Place Details から組み立て
- 外部API呼び出しなし (テンプレベース)
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOPS = ROOT / "data" / "shops.json"
OUT_DIR = ROOT / "outputs" / "instagram"

BASE_TAGS = [
    "#BOKUMO", "#ボクモ", "#北海道グルメ", "#子連れランチ", "#子連れokな店",
    "#札幌グルメ", "#北海道ママ", "#子連れお出かけ", "#キッズメニュー",
    "#子連れ歓迎", "#親子で楽しめる",
]

AREA_TAGS = {
    "札幌": ["#札幌ランチ", "#札幌子連れ"],
    "旭川": ["#旭川グルメ", "#旭川子連れ"],
    "函館": ["#函館グルメ", "#函館子連れ"],
    "帯広": ["#帯広グルメ"],
    "釧路": ["#釧路グルメ"],
    "室蘭": ["#室蘭グルメ"],
}

GENRE_TAGS = {
    "ラーメン": ["#ラーメン好き", "#札幌ラーメン"],
    "カレー": ["#スープカレー"],
    "中華": ["#中華料理"],
    "焼肉": ["#焼肉ディナー"],
    "寿司": ["#寿司"],
    "イタリアン": ["#イタリアン"],
    "和食": ["#和食"],
    "カフェ": ["#カフェ巡り"],
}


def build_caption(shop: dict, details: dict) -> str:
    name = shop["name"]
    area = shop["area"]
    genre = shop["genre"]
    tags = shop.get("tags", [])
    rating = details.get("rating")
    address = details.get("formattedAddress", "")

    lines = [
        f"📍 {name}（{area}）",
        "",
        f"北海道{area}の{genre}。",
    ]
    if tags:
        lines.append("・".join(tags) + "で、子連れでも安心して過ごせます。")
    lines.append("")
    if rating:
        lines.append(f"⭐ Google評価 {rating}")
    if address:
        lines.append(f"🏠 {address}")
    lines.append("")
    lines.append("詳しい情報は BOKUMO（ボクモ）で👇")
    lines.append("https://boku-mo.com/shop/" + str(shop["id"]))
    lines.append("")
    lines.append("━━━━━━━━━━")
    lines.append("BOKUMOは北海道の子連れ歓迎飲食店ガイドです🍽")
    lines.append("プロフィールから他のお店もチェック！")
    lines.append("")

    hashtags = list(BASE_TAGS)
    hashtags += AREA_TAGS.get(area, [])
    hashtags += GENRE_TAGS.get(genre, [])
    lines.append(" ".join(hashtags))

    return "\n".join(lines)


def main() -> None:
    today = date.today().strftime("%Y%m%d")
    day_dir = OUT_DIR / today
    selection_file = day_dir / "selected.json"
    if not selection_file.exists():
        raise SystemExit(f"先に 01_select_shops.py を実行してください")

    selected = json.loads(selection_file.read_text(encoding="utf-8"))
    shops_all = {s["id"]: s for s in json.loads(SHOPS.read_text(encoding="utf-8"))}

    for sel in selected:
        sid = sel["id"]
        shop = shops_all[sid]
        shop_dir = day_dir / f"shop_{sid}"
        details_file = shop_dir / "details.json"
        if not details_file.exists():
            print(f"[{sid}] details.json なし、スキップ")
            continue
        details = json.loads(details_file.read_text(encoding="utf-8"))
        caption = build_caption(shop, details)
        (shop_dir / "caption.txt").write_text(caption, encoding="utf-8")
        print(f"[{sid}] caption.txt 生成 ({len(caption)} chars)")


if __name__ == "__main__":
    main()
