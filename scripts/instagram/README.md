# BOKUMO Instagram 投稿用画像 自動生成

毎日3店舗 × 5枚 = 15枚のInstagram投稿素材を自動生成する。
画像加工は **Pillow (ローカル)** で完結。投稿はスマホから手動。

## 前提
- `.env.local` に `GOOGLE_PLACES_API_KEY` 設定済み
- Python 3 + Pillow インストール済み (`pip install Pillow`)
- `assets/fonts/NotoSansJP-{Bold,Regular}.otf` あり

## 日次フロー

### 1. 画像生成 (1コマンド・数秒で完了)
```bash
python3 scripts/instagram/run_daily.py
```
出力: `outputs/instagram/YYYYMMDD/shop_{id}/`
- `raw/01.jpg〜05.jpg` - Places API元写真
- `processed/01.jpg〜05.jpg` - **テキスト焼き込み済み (1080×1080)**
- `caption.txt` - 投稿文+ハッシュタグ
- `details.json` - Places API詳細

### 2. スマホで投稿 (3店舗ぶん)
1. AirDrop / Google Drive / iCloud で `processed/*.jpg` をスマホへ
2. Instagramを開く → 新規投稿 → カルーセル(複数枚)で5枚選択
3. `caption.txt` の内容をコピペ
4. 投稿

### 3. 履歴記録
```bash
python3 scripts/instagram/mark_posted.py
```
`logs/posted_history.json` に本日のID追記 → 永久に再選定対象から除外。

## ファイル構成
```
scripts/instagram/
├── 01_select_shops.py     本日3店舗選定
├── 02_fetch_photos.py     Places API で写真5枚+詳細取得
├── 03_generate_caption.py キャプション+ハッシュタグ生成
├── 04_render_overlays.py  Pillowでテキスト焼き込み
├── run_daily.py           上記4つを一括実行
└── mark_posted.py         投稿後に履歴追記
```

## 予算ガード
- 月次上限: $150 (Places API 無料枠 $200 の75%)
- `logs/cost_YYYYMM.json` で累計追跡
- 上限到達で自動停止

## スライド構成 (1080×1080)
1. **表紙** - 店名・エリア/ジャンル・BOKUMOバッジ
2. **看板メニュー** - 店名・★評価
3. **店内** - タグ
4. **子連れポイント** - "子連れで安心◎" + タグ
5. **店舗情報** - 住所・営業時間・CTA

## 履歴リセット
全店舗投稿後など、再投稿を許可したい場合は `logs/posted_history.json` の `posted_shop_ids` を `[]` に戻す。
