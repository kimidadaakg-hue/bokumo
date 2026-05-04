# BOKUMO SNS 日次運用ガイド

毎日3店舗 × 6枚の画像を生成し、Instagram に **完全自動で予約投稿** する。
（TikTok は写真モードがモバイル限定なので手動）

## 自動化フロー

| ジョブ | 時刻 | 内容 |
|---|---|---|
| `com.bokumo.daily.plist`  | 毎朝 9:00  | 画像生成パイプライン（`run_daily.py`） |
| `com.bokumo.post.plist`   | 毎日 19:30 | Instagram 予約投稿（`06_post_to_instagram.py`） |

### 9:00 のジョブ：画像生成
- 出力先: `outputs/instagram/{YYYYMMDD}/shop_{id}/`
- 内訳: 3店舗 × 6枚 (1080×1080 IG用) + `tiktok/` (1080×1920) + `caption.txt`
- ついでに `data/shops.json` の `gallery` と `public/photos/gallery/` も更新（`05_sync_gallery.py`）

### 19:30 のジョブ：Instagram 予約投稿
- `06_post_to_instagram.py` が R2 にアップロード後、Instagram Graph API で **翌日19:30公開の予約**を作成
- `scheduled_publish_time` + `published=false` で予約コンテナ作成 → 即時公開はしない
- 24時間のバッファがあるので、内容に問題があれば Meta Business Suite からキャンセル可能
- 成功した店だけ `logs/posted_history.json` に追記され、翌日以降の抽選から除外

## 毎日の手動作業

### TikTok 投稿（iPhoneアプリ）
TikTokは写真モードがモバイル限定なのでiPhone経由：

1. SSDから iPhone に画像6枚をAirDrop
   - 送信元: `outputs/instagram/{YYYYMMDD}/shop_{id}/tiktok/01.jpg〜06.jpg`
2. iPhoneのTikTokアプリ → 「**＋**」 → 「**写真**」モード
3. カメラロールから6枚選択 → 順番確認
4. キャプション欄に `tiktok/caption.txt` を貼り付け
5. シェア（Pro/ビジネスアカウントなら最大10日先まで予約可能）

### サイトのギャラリー反映（git push）
本日の3店舗の raw 写真は自動で `public/photos/gallery/{shop_id}/` にコピー済み。
サイトに反映するには：

```bash
cd /Volumes/外付けSSD/クロード/bokumo
git add data/shops.json public/photos/gallery
git commit -m "Add gallery for today's 3 shops"
git push
```

数分で boku-mo.com の店舗詳細ページにギャラリーグリッドが表示される。

## 手動でパイプラインを再実行したい場合

```bash
cd /Volumes/外付けSSD/クロード/bokumo
python3 scripts/instagram/run_daily.py                       # 画像生成だけ
python3 scripts/instagram/06_post_to_instagram.py --dry-run  # 投稿確認のみ（API叩かない）
python3 scripts/instagram/06_post_to_instagram.py            # 本番投稿（翌日19:30予約）
```

## launchd ジョブの操作

```bash
# 状態確認
launchctl list | grep bokumo

# 手動実行
launchctl start com.bokumo.daily
launchctl start com.bokumo.post

# 停止
launchctl unload ~/Library/LaunchAgents/com.bokumo.daily.plist
launchctl unload ~/Library/LaunchAgents/com.bokumo.post.plist

# 再起動
launchctl load ~/Library/LaunchAgents/com.bokumo.daily.plist
launchctl load ~/Library/LaunchAgents/com.bokumo.post.plist
```

ログ: `~/Library/Logs/bokumo_daily.log` / `~/Library/Logs/bokumo_post.log`

## ファイル構成

```
scripts/instagram/
  run_daily.py             # 一括実行（01→02→02b→03→04→04c→05→copy）
  01_select_shops.py       # 3店舗を抽選（履歴除外）
  02_fetch_photos.py       # Places API で写真10枚 + 詳細取得
  02b_classify_photos.py   # Gemini Vision で食事/内観に分類
  03_generate_caption.py   # キャプション生成
  04_render_overlays.py    # 6枚レンダリング (1080×1080 Instagram用)
  04c_render_tiktok.py     # 6枚を縦版に変換 (1080×1920 TikTok用)
  05_sync_gallery.py       # raw写真をサイトのギャラリーに同期
  copy_to_preview.py       # SSD整理コピー
  06_post_to_instagram.py  # R2アップ → IG カルーセル予約投稿（翌日19:30）
  mark_posted.py           # 投稿履歴に手動追記（通常はpostスクリプトが自動でやる）
  exchange_token.py        # FB Page Token 再発行
```

## ルール詳細
**`/Volumes/外付けSSD/クロード/bokumo/CLAUDE.md` の「インスタ自動投稿ルール」セクション参照。**
変更前に必ず読み返すこと。
