"""raw/*.jpg に映る顔を OpenCV YuNet で検出してガウシアンブラーで隠す。

プライバシー保護のため、Instagram / TikTok 投稿用画像から第三者の顔を消す。

- モデル: assets/models/face_detection_yunet_2023mar.onnx (OpenCV Zoo)
- 検出された各顔領域 + 周囲マージンにガウシアンブラーを適用
- 結果は raw/ に上書き保存
- 二重実行防止: 処理後に raw/.blurred マーカーを作成
- 検出失敗（見落とし）は許容する（ユーザー指定方針: 失敗時はそのまま使う）
"""
import json
from datetime import date
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "instagram"
MODEL_PATH = ROOT / "assets" / "models" / "face_detection_yunet_2023mar.onnx"

# 検出パラメータ
SCORE_THRESHOLD = 0.6   # 0.5 だと誤検出多い、0.7 だと取りこぼし増
NMS_THRESHOLD = 0.3
TOP_K = 50
MARGIN_RATIO = 0.15     # 顔 bbox の周囲 15% を追加でブラー（耳・髪の毛縁を覆う）


def blur_region(img: np.ndarray, x: int, y: int, w: int, h: int) -> None:
    """指定領域にガウシアンブラーを in-place 適用。"""
    H, W = img.shape[:2]
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(W, x + w)
    y2 = min(H, y + h)
    if x2 <= x1 or y2 <= y1:
        return
    roi = img[y1:y2, x1:x2]
    # kernel size は顔サイズに比例、必ず奇数。最小 15 で軽い顔も確実に潰す
    k = max(15, ((max(x2 - x1, y2 - y1) // 4) | 1))
    img[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (k, k), 0)


def detect_and_blur(img_path: Path, detector) -> int:
    """1枚処理してブラーした顔の数を返す。0 なら何も書き換えない。"""
    img = cv2.imread(str(img_path))
    if img is None:
        return 0
    h, w = img.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    if faces is None:
        return 0

    count = 0
    for face in faces:
        # face = [x, y, w, h, eye_l_x, eye_l_y, ..., score]
        x, y, fw, fh = map(int, face[:4])
        margin = int(max(fw, fh) * MARGIN_RATIO)
        blur_region(img, x - margin, y - margin, fw + 2 * margin, fh + 2 * margin)
        count += 1

    cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return count


def process_shop(shop_dir: Path, detector) -> None:
    raw_dir = shop_dir / "raw"
    if not raw_dir.exists():
        print("  raw/ なし、スキップ")
        return
    marker = raw_dir / ".blurred"
    if marker.exists():
        print("  既に処理済み (skip)")
        return

    files = sorted(raw_dir.glob("*.jpg"))
    total_faces = 0
    for f in files:
        n = detect_and_blur(f, detector)
        if n > 0:
            print(f"  {f.name}: 顔 {n} 個をブラー")
        total_faces += n
    marker.touch()
    print(f"  合計 顔 {total_faces} 個 / 写真 {len(files)} 枚")


def main() -> None:
    if not MODEL_PATH.exists():
        raise SystemExit(f"YuNet モデルが見つかりません: {MODEL_PATH}")

    today = date.today().strftime("%Y%m%d")
    day_dir = OUT_DIR / today
    selection_file = day_dir / "selected.json"
    if not selection_file.exists():
        raise SystemExit("先に 01_select_shops.py を実行してください")
    selected = json.loads(selection_file.read_text(encoding="utf-8"))

    detector = cv2.FaceDetectorYN_create(
        str(MODEL_PATH), "", (320, 320),
        score_threshold=SCORE_THRESHOLD,
        nms_threshold=NMS_THRESHOLD,
        top_k=TOP_K,
    )

    for sel in selected:
        sid = sel["id"]
        shop_dir = day_dir / f"shop_{sid}"
        if not shop_dir.exists():
            print(f"[{sid}] shop dir なし、スキップ")
            continue
        print(f"[{sid}] {sel['name']}")
        process_shop(shop_dir, detector)


if __name__ == "__main__":
    main()
