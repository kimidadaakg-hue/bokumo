"""raw 写真5枚 → Pillow でテキストオーバーレイ → processed/ に保存。
1080x1080 のInstagram正方形フォーマットに統一。
日本語フォントは assets/fonts/NotoSansJP-*.otf を使用。
"""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def sanitize(s: str) -> str:
    """絵文字と特殊空白を除去 (Noto Sans JPで表示できない文字対策)"""
    if not s:
        return ""
    # 特殊空白を通常の半角に
    s = s.replace("\u202f", " ").replace("\u2009", " ").replace("\u00a0", " ")
    # 絵文字 (surrogate pair / 補助多言語面) 除去
    out = []
    for ch in s:
        cp = ord(ch)
        if 0x1F000 <= cp <= 0x1FFFF or 0x2600 <= cp <= 0x27BF or cp == 0xFE0F:
            continue
        out.append(ch)
    return "".join(out).strip()

ROOT = Path(__file__).resolve().parents[2]
SHOPS = ROOT / "data" / "shops.json"
OUT_DIR = ROOT / "outputs" / "instagram"
FONT_BOLD = ROOT / "assets" / "fonts" / "NotoSansJP-Bold.otf"
FONT_REG = ROOT / "assets" / "fonts" / "NotoSansJP-Regular.otf"

CANVAS = 1080
PINK = (229, 164, 181)
PINK_DARK = (200, 110, 140)
WHITE = (255, 255, 255)
BLACK = (40, 40, 40)


def fit_square(img: Image.Image) -> Image.Image:
    """中央クロップで 1080x1080 に揃える"""
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2,
                    (w + side) // 2, (h + side) // 2))
    return img.resize((CANVAS, CANVAS), Image.LANCZOS)


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size)


def draw_text_centered(draw, text, y, fnt, color=WHITE, shadow=True):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    w = bbox[2] - bbox[0]
    x = (CANVAS - w) // 2 - bbox[0]
    if shadow:
        draw.text((x + 3, y + 3), text, font=fnt, fill=(0, 0, 0, 180))
    draw.text((x, y), text, font=fnt, fill=color)


def darken(img: Image.Image, alpha: int = 100) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def slide1_cover(raw: Path, name: str, area: str, genre: str) -> Image.Image:
    img = darken(fit_square(Image.open(raw)), 80)
    draw = ImageDraw.Draw(img)
    # 店名 (上部)
    title_size = 84 if len(name) <= 8 else 64 if len(name) <= 14 else 50
    draw_text_centered(draw, name, 140, font(title_size))
    # サブタイトル
    draw_text_centered(draw, f"{area} ・ {genre}", 140 + title_size + 30, font(38, False))
    # BOKUMOバッジ (右下)
    badge_w, badge_h = 220, 64
    bx, by = CANVAS - badge_w - 50, CANVAS - badge_h - 50
    draw.rounded_rectangle((bx, by, bx + badge_w, by + badge_h), radius=32, fill=PINK)
    bf = font(34)
    bbox = draw.textbbox((0, 0), "BOKUMO", font=bf)
    draw.text((bx + (badge_w - (bbox[2] - bbox[0])) // 2 - bbox[0],
               by + (badge_h - (bbox[3] - bbox[1])) // 2 - bbox[1]),
              "BOKUMO", font=bf, fill=WHITE)
    return img


def slide2_menu(raw: Path, name: str, rating, count) -> Image.Image:
    img = fit_square(Image.open(raw))
    draw = ImageDraw.Draw(img)
    band_h = 200
    # ピンク帯 (下部)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, CANVAS - band_h, CANVAS, CANVAS), fill=(*PINK, 220))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw_text_centered(draw, f"{name}", CANVAS - band_h + 30, font(48), shadow=False)
    rating_txt = f"★ {rating}" + (f"  ({count}件)" if count else "")
    draw_text_centered(draw, rating_txt, CANVAS - band_h + 110, font(40, False), shadow=False)
    return img


def slide3_interior(raw: Path, tags: list) -> Image.Image:
    img = fit_square(Image.open(raw))
    band_h = 160
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, CANVAS - band_h, CANVAS, CANVAS), fill=(255, 255, 255, 220))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    txt = " / ".join(tags) if tags else "子連れ歓迎"
    draw_text_centered(draw, txt, CANVAS - band_h + 50,
                       font(46), color=BLACK, shadow=False)
    return img


def slide4_kidpoint(raw: Path, tags: list) -> Image.Image:
    img = darken(fit_square(Image.open(raw)), 130)
    draw = ImageDraw.Draw(img)
    draw_text_centered(draw, "子連れで安心◎", 380, font(96))
    sub = " ・ ".join(tags) if tags else "子連れOK"
    if len(sub) > 28:
        sub = sub[:28] + "…"
    draw_text_centered(draw, sub, 540, font(40, False))
    draw_text_centered(draw, "BOKUMO で詳細をチェック", 760, font(36, False))
    return img


def slide5_info(raw: Path, name: str, address: str, hours: str) -> Image.Image:
    img = fit_square(Image.open(raw))
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 215))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw_text_centered(draw, sanitize(name), 130, font(56), color=BLACK, shadow=False)
    y = 280
    for line in wrap(sanitize(address), 18)[:3]:
        draw_text_centered(draw, line, y, font(34, False), color=BLACK, shadow=False)
        y += 50
    if hours:
        y += 40
        draw_text_centered(draw, "営業時間", y, font(32), color=PINK_DARK, shadow=False)
        y += 50
        for line in wrap(sanitize(hours), 18)[:2]:
            draw_text_centered(draw, line, y, font(30, False), color=BLACK, shadow=False)
            y += 45
    draw_text_centered(draw, "詳しくは『BOKUMO』で検索", CANVAS - 120,
                       font(36), color=PINK_DARK, shadow=False)
    return img


def wrap(text: str, n: int) -> list:
    return [text[i:i + n] for i in range(0, len(text), n)]


def render_shop(shop_dir: Path, shop: dict, details: dict) -> None:
    raw_dir = shop_dir / "raw"
    out_dir = shop_dir / "processed"
    out_dir.mkdir(exist_ok=True)

    name = shop["name"]
    area = shop["area"]
    genre = shop["genre"]
    tags = shop.get("tags", [])
    rating = details.get("rating", "-")
    count = details.get("userRatingCount", 0)
    address = details.get("formattedAddress", "")
    hours_list = details.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
    hours = hours_list[0] if hours_list else ""

    raws = sorted(raw_dir.glob("*.jpg"))
    if len(raws) < 5:
        print(f"  写真不足({len(raws)}枚)、スキップ")
        return

    slides = [
        ("01.jpg", slide1_cover(raws[0], name, area, genre)),
        ("02.jpg", slide2_menu(raws[1], name, rating, count)),
        ("03.jpg", slide3_interior(raws[2], tags)),
        ("04.jpg", slide4_kidpoint(raws[3], tags)),
        ("05.jpg", slide5_info(raws[4], name, address, hours)),
    ]
    for fname, img in slides:
        img.save(out_dir / fname, "JPEG", quality=92)
        print(f"  → processed/{fname}")


def main() -> None:
    today = date.today().strftime("%Y%m%d")
    day_dir = OUT_DIR / today
    selection_file = day_dir / "selected.json"
    if not selection_file.exists():
        raise SystemExit("先に 01_select_shops.py を実行してください")

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
        print(f"[{sid}] {shop['name']}")
        render_shop(shop_dir, shop, details)


if __name__ == "__main__":
    main()
