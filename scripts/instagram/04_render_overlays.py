"""raw/ + classified.json → 6枚のスライドを processed/ に出力。
1: 食事A（シズル感優先・最小限テキスト）
2: 食事B + 上部に半透明ダーク情報パネル
3: 食事C（テキストなし）
4: 店内① + 子連れおすすめ情報
5: 店内②（テキストなし）
6: BOKUMO 宣伝

Instagram のプロフィールグリッドは 4:5 (1080x1350) で表示するため、
1080x1080 だと上下が cropされてテキスト見切れが発生する。
2026-05-06 から 1080x1350 (縦長 4:5) に統一。
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
# 手書き風（学校教科書風） — 親近感とファミリー向けの温かみ
FONT_BOLD = ROOT / "assets" / "fonts" / "KleeOne-SemiBold.ttf"
FONT_REG = ROOT / "assets" / "fonts" / "KleeOne-Regular.ttf"
# マジックペン手書き風（slide1_cover 用、カジュアル & シャープ）
FONT_BRUSH = ROOT / "assets" / "fonts" / "YuseiMagic-Regular.ttf"


def font_brush(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BRUSH), size)


def short_area(area: str) -> str:
    """縦書き表示用に area を 2-3 文字に圧縮."""
    if not area:
        return ""
    if area.startswith("札幌"):
        return "札幌"
    return area[:3]

CANVAS_W = 1080
CANVAS_H = 1350
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
def fit_canvas(img: Image.Image) -> Image.Image:
    """元画像を 1080x1350 (4:5 縦長) にセンタークロップ。

    JPEG 保存できるよう必ず RGB で返す（PNG 等の RGBA 元画像にも対応）。
    """
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    target_ratio = CANVAS_W / CANVAS_H  # 0.8
    src_ratio = w / h
    if src_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x0 = (w - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, h))
    else:
        new_h = int(w / target_ratio)
        y0 = (h - new_h) // 2
        img = img.crop((0, y0, w, y0 + new_h))
    return img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)


# 後方互換のエイリアス
fit_square = fit_canvas


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
def slide1_cover(raw: Path, name: str, area: str, genre: str,
                 tags: list | None = None) -> Image.Image:
    """参考画像風レイアウト（2026-05-06 改訂3）。

    - 左上: 縦書きで地名（極大、筆書き手書きフォント YujiBoku）
    - 右上: BOKUMO ロゴ + サブタイトル
    - 写真メイン（ベタ表示）
    - 下部: キャッチコピー大 + 設備タグ大
    - 全テキストに白フィル + ダークアウトライン
    """
    img = fit_canvas(Image.open(raw))
    draw = ImageDraw.Draw(img)

    # ---- 左上: 縦書きで地名（極大） ----
    v_text = short_area(area)  # "札幌" / "函館" / "旭川" 等
    if v_text:
        v_size = 200
        fnt_v = font_brush(v_size)
        v_x = 60
        v_y = 80
        line_h = int(v_size * 1.05)
        for i, ch in enumerate(v_text):
            draw_outline(
                draw, (v_x, v_y + i * line_h), ch, fnt_v,
                fill=WHITE, stroke=(35, 15, 25), stroke_w=6,
            )

    # ---- 右上: BOKUMO + サブタイトル ----
    # 英字部分は Klee One Bold（筆書きは英字が読みづらいため）
    title = "BOKUMO"
    fnt_title = font(56, True)
    tw, _, tox, _ = text_w(draw, title, fnt_title)
    title_x = CANVAS_W - tw - 60 - tox
    title_y = 70
    draw_outline(
        draw, (title_x, title_y), title, fnt_title,
        fill=WHITE, stroke=(35, 15, 25), stroke_w=4,
    )
    # サブ「by 北海道 子連れガイド」
    sub = "by 北海道 子連れガイド"
    fnt_sub = font(22, False)
    sw, _, sox, _ = text_w(draw, sub, fnt_sub)
    draw_outline(
        draw, (CANVAS_W - sw - 60 - sox, title_y + 80),
        sub, fnt_sub,
        fill=WHITE, stroke=(35, 15, 25), stroke_w=2,
    )
    # ジャンル/ファミリー強調
    if genre:
        tag_g = f"-{genre} 子連れOK-"
        fnt_g = font(20, False)
        gw, _, gox, _ = text_w(draw, tag_g, fnt_g)
        draw_outline(
            draw, (CANVAS_W - gw - 60 - gox, title_y + 115),
            tag_g, fnt_g,
            fill=WHITE, stroke=(35, 15, 25), stroke_w=2,
        )

    # ---- 下部キャッチコピー（極大、手書き） ----
    catch = "子連れに優しいお店"
    fnt_catch = font_brush(110)
    cw, _, cox, _ = text_w(draw, catch, fnt_catch)
    # 大きすぎる場合は段階的に縮小
    for sz in (110, 96, 86, 76):
        fnt_catch = font_brush(sz)
        cw, _, cox, _ = text_w(draw, catch, fnt_catch)
        if cw <= CANVAS_W - 60:
            break
    catch_y = CANVAS_H - 270
    draw_outline(
        draw, ((CANVAS_W - cw) // 2 - cox, catch_y),
        catch, fnt_catch, fill=WHITE,
        stroke=(35, 15, 25), stroke_w=6,
    )

    # ---- 設備タグ（中央、大、手書きフォント） ----
    facility_tags = [t for t in (tags or []) if t and t != "子連れOK"][:3]
    if facility_tags:
        tag_line = "  ・  ".join(facility_tags)
        # フィット試行
        fnt_tag = font_brush(60)
        tw_check, _, _, _ = text_w(draw, tag_line, fnt_tag)
        if tw_check > 900:
            fnt_tag = font_brush(50)
            tw_check, _, _, _ = text_w(draw, tag_line, fnt_tag)
        if tw_check > 900:
            fnt_tag = font_brush(42)
        sz_tag = fnt_tag.size
        tw, _, tox, _ = text_w(draw, tag_line, fnt_tag)
        check_size = 54
        gap = 18
        total_w = tw + check_size + gap
        start_x = (CANVAS_W - total_w) // 2
        tag_y = CANVAS_H - 130

        cy = tag_y + check_size // 2 + sz_tag // 6
        cx = start_x + check_size // 2
        # ピンク丸 (影付き)
        draw.ellipse(
            (cx - check_size // 2 + 4, cy - check_size // 2 + 4,
             cx + check_size // 2 + 4, cy + check_size // 2 + 4),
            fill=(0, 0, 0, 110),
        )
        draw.ellipse(
            (cx - check_size // 2, cy - check_size // 2,
             cx + check_size // 2, cy + check_size // 2),
            fill=PINK,
        )
        # ✓
        draw.line((cx - 11, cy + 3, cx - 2, cy + 12), fill=WHITE, width=6)
        draw.line((cx - 2, cy + 12, cx + 14, cy - 8), fill=WHITE, width=6)

        # タグテキスト（筆書き）
        draw_outline(
            draw, (start_x + check_size + gap - tox, tag_y),
            tag_line, fnt_tag, fill=WHITE,
            stroke=(35, 15, 25), stroke_w=3,
        )

    return img


def slide2_info(raw: Path, name: str, address: str, hours: str, rating, count,
                area: str = "", genre: str = "") -> Image.Image:
    """上部に半透明ダーク情報パネル。写真はしっかり見える。

    エリア・ジャンルは slide1 から移動してきた（2026-05-06）。
    """
    img = fit_canvas(Image.open(raw))

    # 上部に半透明ダークパネル（角丸）— エリア・ジャンル分高さ拡大
    pad = 24
    panel_x1, panel_y1 = pad, pad
    panel_x2, panel_y2 = CANVAS_W - pad, 420
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
    y += sz_nm + 8

    # エリア・ジャンル（slide1 から移動、店名直下に小さく）
    if area or genre:
        loc = " ・ ".join(x for x in (area, genre) if x)
        fnt_loc = font(24, False)
        draw.text((inner_x, y), loc, font=fnt_loc, fill=PINK_SOFT)
        y += 36

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
    return fit_canvas(Image.open(raw))


def slide4_kidpoint(raw: Path, tags: list, area: str, genre: str) -> Image.Image:
    """店内 + 子連れおすすめ。下部に半透明帯のみ、写真メイン。"""
    img = fit_canvas(Image.open(raw))

    # 下部に半透明ダーク帯
    band_h = 280
    img = paste_alpha_rect(img, (0, CANVAS_H - band_h, CANVAS_W, CANVAS_H),
                            (0, 0, 0, 165))
    draw = ImageDraw.Draw(img)

    # FOR KIDS ピル（左寄せ）
    label = "FOR KIDS"
    fnt_lb = font(24)
    lw, lh, lox, loy = text_w(draw, label, fnt_lb)
    pad_x, pad_y = 18, 10
    bx = 50
    by = CANVAS_H - band_h + 32
    draw.rounded_rectangle((bx, by, bx + lw + pad_x * 2, by + lh + pad_y * 2),
                            radius=(lh + pad_y * 2) // 2, fill=PINK)
    draw.text((bx + pad_x - lox, by + pad_y - loy), label, font=fnt_lb, fill=WHITE)

    # 大見出し
    headline = "子連れで安心できる空間"
    fnt_hd, _ = fit_text(draw, headline, max_w=CANVAS_W - 100, base_size=56, min_size=40)
    hw, _, hox, _ = text_w(draw, headline, fnt_hd)
    draw.text(((CANVAS_W - hw) // 2 - hox, CANVAS_H - band_h + 100),
              headline, font=fnt_hd, fill=WHITE)

    # 特徴
    features = [t for t in (tags or []) if t][:3]
    if not features or features == ["子連れOK"]:
        features = (features or []) + [f"{area}の{genre}", "ファミリーで気軽に"]
    elif "子連れOK" in features and len(features) == 1:
        features = features + [f"{area}の{genre}"]
    feat_text = "  ・  ".join(features[:3])
    fnt_f, _ = fit_text(draw, feat_text, max_w=CANVAS_W - 100, base_size=32, min_size=22, bold=False)
    fw, _, fox, _ = text_w(draw, feat_text, fnt_f)
    draw.text(((CANVAS_W - fw) // 2 - fox, CANVAS_H - band_h + 180),
              feat_text, font=fnt_f, fill=(230, 230, 230))

    # 下のCTA
    cta = "詳しくは『BOKUMO』で検索"
    fnt_c = font(26, False)
    cw, _, cox, _ = text_w(draw, cta, fnt_c)
    draw.text(((CANVAS_W - cw) // 2 - cox, CANVAS_H - 50),
              cta, font=fnt_c, fill=(220, 220, 220))
    return img


def slide6_promo() -> Image.Image:
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), CREAM)
    draw = ImageDraw.Draw(img)

    # 上部ピンク帯（装飾のみ）
    draw.rectangle((0, 0, CANVAS_W, 60), fill=PINK)

    # 1080x1350 の中央寄せレイアウト（旧 1080x1080 の y=290 → 比例で y=425 程度）
    y = 360
    for line, sz, color in [
        ("北海道の", 58, INK),
        ("子連れOKなお店を", 64, INK),
        ("ぞくぞく更新中！", 72, PINK_DEEP),
    ]:
        w, _, ox, _ = text_w(draw, line, font(sz))
        draw.text(((CANVAS_W - w) // 2 - ox, y), line, font=font(sz), fill=color)
        y += sz + 20
    y += 60
    draw.line((220, y, CANVAS_W - 220, y), fill=PINK, width=3)
    y += 50

    for line, sz, color in [
        ("詳しくは『BOKUMO』で検索", 46, INK),
        ("フォロー & いいね", 50, PINK_DEEP),
        ("よろしくお願いします！", 44, PINK_DEEP),
    ]:
        w, _, ox, _ = text_w(draw, line, font(sz))
        draw.text(((CANVAS_W - w) // 2 - ox, y), line, font=font(sz), fill=color)
        y += sz + 30

    badge_w, badge_h = 480, 86
    bx = (CANVAS_W - badge_w) // 2
    by = CANVAS_H - 140
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
        ("01.jpg", slide1_cover(food_paths[2], name, area, genre, tags)),
        ("02.jpg", slide2_info(food_paths[1], name, address, hours, rating, count, area, genre)),
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
