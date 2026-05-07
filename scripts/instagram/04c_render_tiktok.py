"""processed/*.jpg (1080×1350) → tiktok/*.jpg (1080×1920) に変換。

縦長 4:5 のカバー/コンテンツ画像を中央に配置し、上下を「同じ画像のブラー拡大版」で埋める。
TikTok・縦長フォーマット用。

スライド別ロジック:
- 0 (カバー): カバー側で BOKUMO ロゴ + 地名 + キャッチを焼き込み済みなのでテキスト追加なし
- 1〜4 (コンテンツ): 上下のぼかし帯に BOKUMO ロゴ + CTA を追加
- 5 (プロモ): 上下にピンク帯 + BOKUMO ロゴ + アカウント情報
"""
import json
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "instagram"
FONT_BOLD = ROOT / "assets" / "fonts" / "NotoSansJP-Bold.otf"
FONT_KLEE = ROOT / "assets" / "fonts" / "KleeOne-SemiBold.ttf"

W, H = 1080, 1920
SRC_W, SRC_H = 1080, 1350           # processed/ の実サイズ（4:5）
PAD_TOP = (H - SRC_H) // 2          # 285
PAD_BOTTOM = H - SRC_H - PAD_TOP    # 285

PINK = (224, 91, 124)
PINK_DEEP = (175, 58, 92)
CREAM = (253, 247, 240)
WHITE = (255, 255, 255)


def font(sz: int, bold: bool = True):
    path = FONT_BOLD if bold else FONT_KLEE
    return ImageFont.truetype(str(path), sz)


def text_w(draw, text, fnt):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[0], bbox[1]


def draw_centered(draw, text, y, fnt, color, x_center=W // 2):
    w, _, ox, _ = text_w(draw, text, fnt)
    draw.text((x_center - w // 2 - ox, y), text, font=fnt, fill=color)


def make_blur_bg(src_img: Image.Image) -> Image.Image:
    """元画像を縦長サイズに拡大→強くブラー → 背景にする"""
    bg = src_img.resize((W, int(src_img.height * W / src_img.width)),
                        Image.LANCZOS)
    if bg.height < H:
        bg = bg.resize((int(W * H / bg.height), H), Image.LANCZOS)
    left = (bg.width - W) // 2
    top = (bg.height - H) // 2
    bg = bg.crop((left, top, left + W, top + H))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 90))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    return bg


def make_vertical(src_path: Path, slide_index: int) -> Image.Image:
    """1080×1350 から 1080×1920 を作る"""
    src = Image.open(src_path).convert("RGB")
    # サイズ正規化（万一違うサイズが混ざっても保険）
    if src.size != (SRC_W, SRC_H):
        src = src.resize((SRC_W, SRC_H), Image.LANCZOS)

    # 6枚目（プロモ）はピンク帯 + 中央配置
    if slide_index == 5:
        canvas = Image.new("RGB", (W, H), CREAM)
        d0 = ImageDraw.Draw(canvas)
        d0.rectangle((0, 0, W, PAD_TOP), fill=PINK)
        d0.rectangle((0, H - PAD_BOTTOM, W, H), fill=PINK)
    else:
        canvas = make_blur_bg(src)

    # 中央に元画像を配置
    canvas.paste(src, (0, PAD_TOP))

    draw = ImageDraw.Draw(canvas)

    if slide_index == 0:
        # カバー: 既にロゴ・地名・キャッチが焼き込み済みなのでテキスト追加なし
        pass
    elif slide_index == 5:
        # プロモ: ピンク帯にロゴ + アカウント情報
        draw_centered(draw, "BOKUMO", 80, font(96), color=WHITE)
        draw_centered(draw, "for Hokkaido families", 200, font(34), color=WHITE)
        cta_y = PAD_TOP + SRC_H + 70
        draw_centered(draw, "@bokumo2026", cta_y, font(64), color=WHITE)
        draw_centered(draw, "boku-mo.com", cta_y + 100, font(40), color=WHITE)
    else:
        # コンテンツ写真 (1〜4): 上下のぼかし帯に BOKUMO + CTA
        draw_centered(draw, "BOKUMO", 75, font(80), color=WHITE)
        draw_centered(draw, "北海道の子連れOKなお店", 185, font(34), color=WHITE)

        cta_y = PAD_TOP + SRC_H + 60
        draw_centered(draw, "詳しくは『BOKUMO』で検索", cta_y, font(40), color=WHITE)
        draw_centered(draw, "@bokumo2026 をフォロー", cta_y + 80, font(34), color=WHITE)

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
