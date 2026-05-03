# BOKUMO SNS 日次運用ガイド

毎日3店舗 × 6枚の画像を生成し、Instagram (Meta Business Suite) と TikTok に予約投稿する。

## 自動化されている部分

`launchd` で **毎朝 9:00** に `run_daily.py` が自動実行され、画像とキャプションが整理されてSSDに用意されます。

- 出力先: `/Volumes/外付けSSD/インスタ画像/YYYY-MM-DD/`
- 内訳: 3店舗ぶんのフォルダ × 各6枚画像（Instagram用1080×1080）+ caption.txt
  - 各フォルダ内に `tiktok/` サブフォルダ（TikTok用1080×1920 + caption.txt）

## 毎日の手動作業（5分程度）

### ステップ1: 画像確認
- Finderで `/Volumes/外付けSSD/インスタ画像/{今日の日付}/` を開く
- 3店舗ぶんの画像とキャプションをチェック

### ステップ2-A: Instagram 予約投稿（Meta Business Suite）

各店舗フォルダごとに以下を3回繰り返す：

1. https://business.facebook.com/latest/composer/ を開く
2. 「写真/動画を追加」→ **正方形画像6枚**を選択（01.jpg〜06.jpg、tiktok/フォルダ内のではなく直下のもの）
3. キャプション欄に `caption.txt` の内容を貼り付け
4. スケジュール → 日時を設定（例：1店舗目18:30、2店舗目19:30、3店舗目20:30など）
5. 「Schedule」をクリック

### ステップ2-B: TikTok 投稿（iPhoneアプリ手動）

TikTokは写真モードがモバイル限定なのでiPhone経由：

1. SSDから iPhone に画像6枚をAirDrop
   - 送信元: `/Volumes/外付けSSD/インスタ画像/{日付}/{店舗フォルダ}/tiktok/01.jpg〜06.jpg`
   - iPhone側で「写真」アプリに保存
2. iPhoneのTikTokアプリを開く
3. 下部「**＋**」 → 「**写真**」モード
4. カメラロールから6枚選択 → 順番確認
5. キャプション欄に `tiktok/caption.txt` の内容を貼り付け
6. シェア（Pro/ビジネスアカウントなら最大10日先まで予約可能）

### ステップ3: 投稿履歴を更新
ターミナルで以下を実行：
```bash
python3 /Volumes/外付けSSD/クロード/bokumo/scripts/instagram/mark_posted.py
```

これで本日の3店舗が「投稿済み」リストに追加され、翌日以降の選定から除外される。

### ステップ4: サイトのギャラリー反映
本日の3店舗の raw 写真は自動的に `public/photos/gallery/{shop_id}/` にコピーされ、
`data/shops.json` の `gallery` フィールドが更新されています。サイトに反映するには：

```bash
cd /Volumes/外付けSSD/クロード/bokumo
git add data/shops.json public/photos/gallery
git commit -m "Add gallery for today's 3 shops"
git push
```

数分でboku-mo.com の店舗詳細ページにギャラリーグリッドが表示されます。

## 手動でパイプラインを再実行したい場合

```bash
cd /Volumes/外付けSSD/クロード/bokumo
python3 scripts/instagram/run_daily.py
```

## launchd ジョブの操作

```bash
# 状態確認
launchctl list | grep bokumo

# 手動実行
launchctl start com.bokumo.daily

# 停止
launchctl unload ~/Library/LaunchAgents/com.bokumo.daily.plist

# 再起動
launchctl load ~/Library/LaunchAgents/com.bokumo.daily.plist
```

## ファイル構成

```
scripts/instagram/
  run_daily.py          # 一括実行（01→02→02b→03→04→copy）
  01_select_shops.py    # 3店舗を抽選（履歴除外）
  02_fetch_photos.py    # Places API で写真10枚 + 詳細取得
  02b_classify_photos.py # Gemini Vision で食事/内観に分類
  03_generate_caption.py # キャプション生成
  04_render_overlays.py  # 6枚レンダリング (1080×1080 Instagram用)
  04c_render_tiktok.py   # 6枚を縦版に変換 (1080×1920 TikTok用)
  05_sync_gallery.py    # raw写真をサイトのギャラリーに同期 (data/shops.json + public/photos/gallery/)
  copy_to_preview.py    # SSD整理コピー
  mark_posted.py        # 投稿履歴に追記（手動実行）
```

## スライド構成 (1080×1080)

| 枚 | 写真 | テキスト |
|---|---|---|
| 1 | 食事A | 「今日のおすすめ」+ 店名 + BOKUMOロゴ |
| 2 | 食事B | 半透明パネル：店名・★評価・住所・営業時間 |
| 3 | 食事C | テキストなし（食事優先） |
| 4 | 店内① | FOR KIDS + 子連れで安心できる空間 |
| 5 | 店内② | テキストなし |
| 6 | 宣伝 | BOKUMO紹介・boku-mo.com・フォローお願い |

## 予算ガード

- Places API 月次上限: $150（無料枠 $200 の75%）
- Gemini API: 無料枠内
- `logs/cost_YYYYMM.json` で累計追跡

## 履歴リセット

全店舗投稿後など、再投稿を許可したい場合は `logs/posted_history.json` の `posted_shop_ids` を `[]` に戻す。

## トラブル時

- **SSDが接続されてない時に9:00を迎えた** → スキップされる。SSD繋いで `python3 scripts/instagram/run_daily.py` を手動実行
- **Macがスリープ中だった** → 起動時に追いかけ実行されない。手動実行が必要
- **画像が変な感じ** → `04_render_overlays.py` のデザイン部分を編集して再実行
