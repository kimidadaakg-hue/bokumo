"""raw/ + classified.json → 6枚のスライドを processed/ に出力。
1: 食事A（シズル感優先・最小限テキスト）
2: 食事B + 上部に半透明ダーク情報パネル
3: 食事C（テキストなし）
4: 店内① + 子連れおすすめ情報
5: 店内②（テキストなし）
6: BOKUMO 宣伝
"""
import json
import re
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def sanitize(s: str) -> str:
    if not s:
        return ""
    s = s.replace(" ", " ").replace(" ", " ").replace(" ", " ")
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
PINK = (224, 91, 124)
PINK_DEEP = (175, 58, 92)
PINK_SOFT = (251, 232, 238)
CREAM = (253, 247, 240)
INK = (38, 38, 42)
GRAY = (130, 130, 135)
GOLD = (212, 175, 55)
WHITE = (255, 255, 255)
DARK_PANEL = (28, 28, 32)


# ---------- ユーティリティ ----------
def fit_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2,
                    (w + side) // 2, (h + side) // 2))
    return img.resize((CANVAS, CANVAS), Image.LANCZOS)


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size)


def text_w(draw, text, fnt):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[0], bbox[1]


def draw_outline(draw, xy, text, fnt, fill, stroke=(0, 0, 0), stroke_w=2):
    """文字に輪郭を付けて視認性を確保（ぼかしを使わずに）"""
    x, y = xy
    for dx in range(-stroke_w, stroke_w + 1):
        for dy in range(-stroke_w, stroke_w + 1):
            if dx * dx + dy * dy <= stroke_w * stroke_w + 1:
                draw.text((x + dx, y + dy), text, font=fnt, fill=stroke)
    draw.text((x, y), text, font=fnt, fill=fill)


def paste_alpha_rect(img: Image.Image, xy, color_rgba) -> Image.Image:
    """半透明の矩形を貼る（角丸対応）"""
    x1, y1, x2, y2 = xy
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((x1, y1, x2, y2), fill=color_rgba)
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def paste_alpha_rounded(img: Image.Image, xy, color_rgba, radius=24) -> Image.Image:
    x1, y1, x2, y2 = xy
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=color_rgba)
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def smart_wrap_address(addr: str, max_chars: int = 22) -> list:
    addr = sanitize(addr)
    m = re.match(r"^(〒\d{3}-\d{4})\s*(.+)$", addr)
    body = m.group(2) if m else addr
    if len(body) <= max_chars:
        return [body]
    for sep in ["市", "区"]:
        idx = body.find(sep)
        if 0 < idx < len(body) - 1:
            line1 = body[:idx + 1]
            rest = body[idx + 1:]
            if len(rest) > max_chars:
                idx2 = rest.find("丁目")
                if 0 < idx2:
                    return [line1, rest[:idx2 + 2], rest[idx2 + 2:]] if rest[idx2 + 2:] else [line1, rest[:idx2 + 2]]
            return [line1, rest]
    return [body[i:i + max_chars] for i in range(0, len(body), max_chars)]


def fit_text(draw, text, max_w, base_size, bold=True, min_size=24):
    sz = base_size
    while sz >= min_size:
        f = font(sz, bold)
        w, _, _, _ = text_w(draw, text, f)
        if w <= max_w:
            return f, sz
        sz -= 4
    return font(min_size, bold), min_size


def draw_home_icon(draw, x, y, size=24, color=WHITE):
    """家アイコン（線画）"""
    s = size
    # 屋根（三角）
    draw.polygon([(x, y + s * 0.5), (x + s * 0.5, y), (x + s, y + s * 0.5)],
                 outline=color, width=2)
    # 本体（四角）
    draw.rectangle((x + s * 0.15, y + s * 0.5, x + s * 0.85, y + s),
                   outline=color, width=2)


def draw_clock_icon(draw, x, y, size=24, color=WHITE):
    """時計アイコン（円＋針）"""
    s = size
    draw.ellipse((x, y, x + s, y + s), outline=color, width=2)
    cx, cy = x + s / 2, y + s / 2
    # 短針（上）
    draw.line((cx, cy, cx, cy - s * 0.3), fill=color, width=2)
    # 長針（右）
    draw.line((cx, cy, cx + s * 0.32, cy), fill=color, width=2)


def draw_star_icon(draw, x, y, size=24, color=GOLD):
    """五芒星（簡易）"""
    import math
    s = size / 2
    cx, cy = x + s, y + s
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        r = s if i % 2 == 0 else s * 0.45
        pts.append((cx + r * math.cos(ang), cy - r * math.sin(ang)))
    draw.polygon(pts, fill=color)


# ---------- スライド ----------
def slide1_cover(raw: Path, name: str, area: str, genre: str) -> Image.Image:
    """シズル感優先。写真は暗くせず、上下に薄帯のみ。"""
    img = fit_square(Image.open(raw))

    # 上部の白いリボン（左寄せ・小さく）
    ribbon_w, ribbon_h = 180, 90
    img = paste_alpha_rect(img, (40, 0, 40 + ribbon_w, ribbon_h), (255, 255, 255, 240))
    # リボン下部の三角形（旗の切れ込み風）
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.polygon([(40, ribbon_h), (40 + ribbon_w / 2, ribbon_h - 22),
                (40 + ribbon_w, ribbon_h)], fill=(255, 255, 255, 240))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    # リボン中身
    draw.text((40 + ribbon_w / 2 - text_w(draw, "今日の", font(24))[0] / 2, 16),
              "今日の", font=font(24), fill=PINK_DEEP)
    draw.text((40 + ribbon_w / 2 - text_w(draw, "おすすめ", font(28))[0] / 2, 44),
              "おすすめ", font=font(28), fill=PINK_DEEP)

    # 下部に細い半透明ダーク帯（シズル感を残しつつ店名を読ませる）
    band_h = 200
    img = paste_alpha_rect(img, (0, CANVAS - band_h, CANVAS, CANVAS),
                            (0, 0, 0, 150))
    draw = ImageDraw.Draw(img)

    # エリア・ジャンル（小さく・薄く）
    sub = f"{area} ・ {genre}"
    fnt_sub = font(28, False)
    sw, _, sox, _ = text_w(draw, sub, fnt_sub)
    draw.text(((CANVAS - sw) // 2 - sox, CANVAS - band_h + 24),
              sub, font=fnt_sub, fill=(255, 255, 255, 220))

    # 店名（大きく）
    nm = sanitize(name)
    fnt_nm, _ = fit_text(draw, nm, max_w=920, base_size=64, min_size=36)
    nw, _, nox, _ = text_w(draw, nm, fnt_nm)
    draw.text(((CANVAS - nw) // 2 - nox, CANVAS - band_h + 70),
              nm, font=fnt_nm, fill=WHITE)

    # 区切り線
    line_y = CANVAS - 50
    draw.line(((CANVAS - 80) // 2, line_y, (CANVAS + 80) // 2, line_y),
              fill=(255, 255, 255, 180), width=2)

    # BOKUMO（小さく中央下）
    bf = font(26)
    bw, _, box, _ = text_w(draw, "BOKUMO", bf)
    draw.text(((CANVAS - bw) // 2 - box, CANVAS - 38),
              "BOKUMO", font=bf, fill=WHITE)
    return img


def slide2_info(raw: Path, name: str, address: str, hours: str, rating, count) -> Image.Image:
    """上部に半透明ダーク情報パネル。写真はしっかり見える。"""
    img = fit_square(Image.open(raw))

    # 上部に半透明ダークパネル（角丸）
    pad = 24
    panel_x1, panel_y1 = pad, pad
    panel_x2, panel_y2 = CANVAS - pad, 380
    img = paste_alpha_rounded(img, (panel_x1, panel_y1, panel_x2, panel_y2),
                              (*DARK_PANEL, 195), radius=20)
    draw = ImageDraw.Draw(img)

    inner_x = panel_x1 + 36
    inner_w = panel_x2 - panel_x1 - 72
    y = panel_y1 + 28

    # 店名
    nm = sanitize(name)
    fnt_nm, sz_nm = fit_text(draw, nm, max_w=inner_w, base_size=52, min_size=32)
    draw.text((inner_x, y), nm, font=fnt_nm, fill=WHITE)
    y += sz_nm + 18

    # ★評価
    if rating and rating != "-":
        rating_f = float(rating)
        # 星アイコン5つ
        sx = inner_x
        for i in range(5):
            color = GOLD if i < round(rating_f) else (255, 255, 255, 90)
            draw_star_icon(draw, sx, y + 2, size=26, color=color)
            sx += 32
        # 数字
        rt = f"{rating}" + (f"  ({count}件)" if count else "")
        draw.text((sx + 8, y + 2), rt, font=font(24, False), fill=(230, 230, 230))
        y += 44

    # 細い区切り線
    draw.line((inner_x, y, panel_x2 - 36, y), fill=(255, 255, 255, 60), width=1)
    y += 18

    # 住所
    if address:
        draw_home_icon(draw, inner_x, y + 2, size=26, color=PINK_SOFT)
        addr_lines = smart_wrap_address(address, max_chars=22)
        addr_short = addr_lines[0] if addr_lines else ""
        if len(addr_lines) > 1:
            addr_short = addr_short + addr_lines[1]
        # 1行に収める
        fnt_a, _ = fit_text(draw, addr_short, max_w=inner_w - 44, base_size=26, min_size=18, bold=False)
        draw.text((inner_x + 40, y - 2), addr_short, font=fnt_a, fill=(240, 240, 240))
        y += 42

    # 営業時間
    if hours:
        draw_clock_icon(draw, inner_x, y + 2, size=26, color=PINK_SOFT)
        h_clean = sanitize(hours)
        h_clean = re.sub(r"(\d+)時(\d+)分", r"\1:\2", h_clean)
        h_clean = h_clean.replace("〜", "–").replace("～", "–")
        h_clean = re.sub(r"^([月火水木金土日])曜日:\s*", r"\1曜  ", h_clean)
        fnt_h, _ = fit_text(draw, h_clean, max_w=inner_w - 44, base_size=26, min_size=18, bold=False)
        draw.text((inner_x + 40, y - 2), h_clean, font=fnt_h, fill=(240, 240, 240))
    return img


def slide_plain(raw: Path) -> Image.Image:
    return fit_square(Image.open(raw))


def slide4_kidpoint(raw: Path, tags: list, area: str, genre: str) -> Image.Image:
    """店内 + 子連れおすすめ。下部に半透明帯のみ、写真メイン。"""
    img = fit_square(Image.open(raw))

    # 下部に半透明ダーク帯
    band_h = 280
    img = paste_alpha_rect(img, (0, CANVAS - band_h, CANVAS, CANVAS),
                            (0, 0, 0, 165))
    draw = ImageDraw.Draw(img)

    # FOR KIDS ピル（左寄せ）
    label = "FOR KIDS"
    fnt_lb = font(24)
    lw, lh, lox, loy = text_w(draw, label, fnt_lb)
    pad_x, pad_y = 18, 10
    bx = 50
    by = CANVAS - band_h + 32
    draw.rounded_rectangle((bx, by, bx + lw + pad_x * 2, by + lh + pad_y * 2),
                            radius=(lh + pad_y * 2) // 2, fill=PINK)
    draw.text((bx + pad_x - lox, by + pad_y - loy), label, font=fnt_lb, fill=WHITE)

    # 大見出し
    headline = "子連れで安心できる空間"
    fnt_hd, _ = fit_text(draw, headline, max_w=CANVAS - 100, base_size=56, min_size=40)
    hw, _, hox, _ = text_w(draw, headline, fnt_hd)
    draw.text(((CANVAS - hw) // 2 - hox, CANVAS - band_h + 100),
              headline, font=fnt_hd, fill=WHITE)

    # 特徴
    features = [t for t in (tags or []) if t][:3]
    if not features or features == ["子連れOK"]:
        features = (features or []) + [f"{area}の{genre}", "ファミリーで気軽に"]
    elif "子連れOK" in features and len(features) == 1:
        features = features + [f"{area}の{genre}"]
    feat_text = "  ・  ".join(features[:3])
    fnt_f, _ = fit_text(draw, feat_text, max_w=CANVAS - 100, base_size=32, min_size=22, bold=False)
    fw, _, fox, _ = text_w(draw, feat_text, fnt_f)
    draw.text(((CANVAS - fw) // 2 - fox, CANVAS - band_h + 180),
              feat_text, font=fnt_f, fill=(230, 230, 230))

    # 下のCTA
    cta = "詳しくは『BOKUMO』で検索"
    fnt_c = font(26, False)
    cw, _, cox, _ = text_w(draw, cta, fnt_c)
    draw.text(((CANVAS - cw) // 2 - cox, CANVAS - 50),
              cta, font=fnt_c, fill=(220, 220, 220))
    return img


def slide6_promo() -> Image.Image:
    img = Image.new("RGB", (CANVAS, CANVAS), CREAM)
    draw = ImageDraw.Draw(img)

    # 上部ピンク帯（装飾のみ）
    draw.rectangle((0, 0, CANVAS, 60), fill=PINK)

    y = 290
    for line, sz, color in [
        ("北海道の", 58, INK),
        ("子連れOKなお店を", 64, INK),
        ("ぞくぞく更新中！", 72, PINK_DEEP),
    ]:
        w, _, ox, _ = text_w(draw, line, font(sz))
        draw.text(((CANVAS - w) // 2 - ox, y), line, font=font(sz), fill=color)
        y += sz + 20
    y += 60
    draw.line((220, y, CANVAS - 220, y), fill=PINK, width=3)
    y += 50

    for line, sz, color in [
        ("詳しくは『BOKUMO』で検索", 46, INK),
        ("フォロー & いいね", 50, PINK_DEEP),
        ("よろしくお願いします！", 44, PINK_DEEP),
    ]:
        w, _, ox, _ = text_w(draw, line, font(sz))
        draw.text(((CANVAS - w) // 2 - ox, y), line, font=font(sz), fill=color)
        y += sz + 30

    badge_w, badge_h = 480, 86
    bx = (CANVAS - badge_w) // 2
    by = CANVAS - 120
    draw.rounded_rectangle((bx, by, bx + badge_w, by + badge_h), radius=43, fill=PINK)
    bw, bh, ox, oy = text_w(draw, "boku-mo.com", font(40))
    draw.text((bx + (badge_w - bw) // 2 - ox, by + (badge_h - bh) // 2 - oy),
              "boku-mo.com", font=font(40), fill=WHITE)
    return img


# ---------- メイン ----------
def render_shop(shop_dir: Path, shop: dict, details: dict) -> None:
    raw_dir = shop_dir / "raw"
    out_dir = shop_dir / "processed"
    out_dir.mkdir(exist_ok=True)

    classified_file = shop_dir / "classified.json"
    if not classified_file.exists():
        print("  classified.json なし")
        return
    cls = json.loads(classified_file.read_text(encoding="utf-8"))
    food_paths = [shop_dir / p for p in cls.get("food", [])]
    interior_paths = [shop_dir / p for p in cls.get("interior", [])]
    if len(food_paths) < 3 or len(interior_paths) < 2:
        print(f"  写真不足: food={len(food_paths)} interior={len(interior_paths)}")
        return

    name = shop["name"]
    area = shop.get("area", "")
    genre = shop.get("genre", "")
    tags = shop.get("tags", [])
    rating = details.get("rating", "-")
    count = details.get("userRatingCount", 0)
    address = details.get("formattedAddress", "")
    hours_list = details.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
    hours = hours_list[0] if hours_list else ""

    slides = [
        # 食事写真の割り当て:
        # food_paths[2] (3番目に選ばれた料理写真) をカバーに使う方が
        # クオリティ的に良いことが多いため、food[0] と food[2] を入れ替えて表示。
        ("01.jpg", slide1_cover(food_paths[2], name, area, genre)),
        ("02.jpg", slide2_info(food_paths[1], name, address, hours, rating, count)),
        ("03.jpg", slide_plain(food_paths[0])),
        ("04.jpg", slide4_kidpoint(interior_paths[0], tags, area, genre)),
        ("05.jpg", slide_plain(interior_paths[1])),
        ("06.jpg", slide6_promo()),
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
