"""processed/*.jpg (1080×1080) → tiktok/*.jpg (1080×1920) に変換。
正方形画像を中央に配置し、上下を「同じ画像のブラー拡大版」で埋める。
TikTok・縦長フォーマット用。
"""
import json
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "instagram"
FONT_BOLD = ROOT / "assets" / "fonts" / "NotoSansJP-Bold.otf"

W, H = 1080, 1920
SQUARE = 1080
PAD_TOP = (H - SQUARE) // 2  # 420
PAD_BOTTOM = H - SQUARE - PAD_TOP

PINK = (224, 91, 124)
PINK_DEEP = (175, 58, 92)
CREAM = (253, 247, 240)
WHITE = (255, 255, 255)


def font(sz: int):
    return ImageFont.truetype(str(FONT_BOLD), sz)


def text_w(draw, text, fnt):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[0], bbox[1]


def draw_centered(draw, text, y, fnt, color, x_center=W // 2):
    w, _, ox, _ = text_w(draw, text, fnt)
    draw.text((x_center - w // 2 - ox, y), text, font=fnt, fill=color)


def make_blur_bg(square_img: Image.Image) -> Image.Image:
    """正方形画像を縦長サイズに拡大→強くブラー → 背景にする"""
    # 横幅基準で拡大
    bg = square_img.resize((W, int(square_img.height * W / square_img.width)),
                            Image.LANCZOS)
    # 高さがHに足りなければ更に拡大
    if bg.height < H:
        bg = bg.resize((int(W * H / bg.height), H), Image.LANCZOS)
    # 中央クロップで W×H に
    left = (bg.width - W) // 2
    top = (bg.height - H) // 2
    bg = bg.crop((left, top, left + W, top + H))
    # ブラー
    bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
    # 暗くして主役を引き立てる
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 90))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    return bg


def make_vertical(square_path: Path, slide_index: int) -> Image.Image:
    """正方形画像から1080×1920を作る"""
    sq = Image.open(square_path)
    # 6枚目（プロモ）は背景なしでクリーム単色
    if slide_index == 5:
        canvas = Image.new("RGB", (W, H), CREAM)
        # 上下に少しピンクの帯
        ImageDraw.Draw(canvas).rectangle((0, 0, W, PAD_TOP), fill=PINK)
        ImageDraw.Draw(canvas).rectangle((0, H - PAD_BOTTOM, W, H), fill=PINK)
    else:
        canvas = make_blur_bg(sq)

    # 中央に正方形を配置
    canvas.paste(sq, (0, PAD_TOP))

    # 上部にロゴ・下部にCTA
    draw = ImageDraw.Draw(canvas)
    if slide_index != 5:
        # 上部: BOKUMO ロゴ
        draw_centered(draw, "BOKUMO", 110, font(96), color=WHITE)
        draw_centered(draw, "北海道の子連れOKなお店", 230, font(40), color=WHITE)

        # 下部: CTA
        cta_y = PAD_TOP + SQUARE + 80
        draw_centered(draw, "詳しくは『BOKUMO』で検索", cta_y, font(48), color=WHITE)
        draw_centered(draw, "@bokumo2026 をフォロー", cta_y + 90, font(40), color=WHITE)
    else:
        # 6枚目はカバー画像が中央にあるだけ。上下のピンク帯にテキスト
        draw_centered(draw, "BOKUMO", 130, font(110), color=WHITE)
        draw_centered(draw, "for Hokkaido families", 270, font(34), color=WHITE)
        cta_y = PAD_TOP + SQUARE + 110
        draw_centered(draw, "@bokumo2026", cta_y, font(64), color=WHITE)
        draw_centered(draw, "boku-mo.com", cta_y + 100, font(50), color=WHITE)

    return canvas


def render_shop(shop_dir: Path) -> None:
    proc_dir = shop_dir / "processed"
    out_dir = shop_dir / "tiktok"
    if not proc_dir.exists():
        print("  processed/ なし、スキップ")
        return
    out_dir.mkdir(exist_ok=True)
    files = sorted(proc_dir.glob("*.jpg"))
    if len(files) < 6:
        print(f"  画像不足: {len(files)}枚")
        return
    for i, f in enumerate(files):
        img = make_vertical(f, i)
        img.save(out_dir / f.name, "JPEG", quality=92)
        print(f"  → tiktok/{f.name}")


def main() -> None:
    today = date.today().strftime("%Y%m%d")
    day_dir = OUT_DIR / today
    selection_file = day_dir / "selected.json"
    if not selection_file.exists():
        raise SystemExit("先に 01_select_shops.py を実行してください")
    selected = json.loads(selection_file.read_text(encoding="utf-8"))
    for sel in selected:
        sid = sel["id"]
        shop_dir = day_dir / f"shop_{sid}"
        if not shop_dir.exists():
            print(f"[{sid}] shop dir なし、スキップ")
            continue
        print(f"[{sid}] {sel['name']}")
        render_shop(shop_dir)


if __name__ == "__main__":
    main()
