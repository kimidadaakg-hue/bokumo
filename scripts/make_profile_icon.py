"""Instagram プロフィールアイコン (1080x1080)"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_BOLD = ROOT / "assets" / "fonts" / "NotoSansJP-Bold.otf"
OUT = ROOT / "outputs" / "profile_icon.jpg"

SIZE = 1080
PINK = (224, 91, 124)
PINK_DEEP = (175, 58, 92)
CREAM = (253, 247, 240)


def font(sz: int):
    return ImageFont.truetype(str(FONT_BOLD), sz)


def text_w(draw, text, fnt):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[0], bbox[1]


def main():
    # ピンク背景
    img = Image.new("RGB", (SIZE, SIZE), PINK)
    draw = ImageDraw.Draw(img)

    # 中央のクリーム円
    margin = 80
    draw.ellipse((margin, margin, SIZE - margin, SIZE - margin), fill=CREAM)

    # 上下の細い装飾ライン
    cx = SIZE // 2
    line_len = 110
    draw.line((cx - line_len, 360, cx + line_len, 360), fill=PINK, width=4)
    draw.line((cx - line_len, 720, cx + line_len, 720), fill=PINK, width=4)

    # 「BOKUMO」中央
    fnt = font(180)
    w, h, ox, oy = text_w(draw, "BOKUMO", fnt)
    x = (SIZE - w) // 2 - ox
    y = (SIZE - h) // 2 - oy
    draw.text((x, y), "BOKUMO", font=fnt, fill=PINK_DEEP)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "JPEG", quality=95)
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
