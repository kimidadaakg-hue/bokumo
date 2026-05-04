# BOKUMO 開発ルール

## ⚠️ 絶対遵守（NEVER FORGET）

**このファイルのルールは、ユーザーから明示的な変更指示があるまで、無条件に守ること。**
**「サクッと追加で」「ちょっと試しに」も含めて例外なし。** 過去に緩めて誤情報を多数追加し、
ユーザー信頼を損ねる事故を起こしている。新しいセッションでも、shops.json を触る前に
必ずこのファイルを読み返すこと。

---

## 店舗データ追加時の必須フィルタ（v2 / 2026-05-02）

新規店舗を `data/shops.json` に追加する場合、以下のルールを必ずすべて満たすこと。

### ① 全経路共通：店名ベースの除外（fetch時に必ず適用）
- **チェーン店除外**: `scripts/get_shops_hotpepper.py` の `is_chain()` で60+キーワード
- **店名NG除外**: `has_excluded_name()` でゴルフバー / ラウンジ / スナック / CLUB / BAR / Bar / バル系
- **Google Places type除外**: `bar` / `night_club` / `liquor_store`
- **ジャンル除外**:
  - Hotpepper: `EXCLUDED_GENRE_KEYWORDS`（居酒屋/フレンチ/イタリアン/ダイニングバー/バル/ビアガーデン）
  - Google Places: `EXCLUDED_GENRE_KEYWORDS_GPLACES`（ダイニングバー/バル/ビアガーデン のみ）

### ② Hotpepper 経路（厳しめ）

| # | フィルタ | 内容 |
|---|---|---|
| 1 | API側 | `child=1`（お子様連れOK店のみ） |
| 2 | 重複除外 | hotpepper id |
| 3-5 | 共通フィルタ | チェーン / 店名NG / ジャンル除外 |
| 6 | **🔒 説明文に子連れキーワード必須** | `キッズチェア` `子供用椅子` `ベビーチェア` `ハイチェア` `キッズメニュー` `お子様メニュー` `子供メニュー` `お子様ランチ` `ベビーカー` `ストローラー` のいずれか1個以上 (has_hotpepper_kid_keyword()) |
| 7 | **「中」モード必須** | `ベビーカーOK` / `キッズチェアあり` / `子供メニューあり` のうち1個以上必須 |

**Hotpepper のタグ付与ルール（永続）**:
- ✅ ベビーカーOK = 説明文に「ベビーカー」「ストローラー」明記のみ
- ✅ キッズチェアあり = 上記キーワードリスト
- ✅ 子供メニューあり = 上記キーワードリスト
- ❌ **`barrier_free=あり` を ベビーカーOK に自動付与しない**（誤判定多すぎ）
- ❌ **`座敷あり` `個室あり` のタグは Hotpepper からは付与しない**（飲み会用途が多い）

### ③ Google Places + Gemini 経路（緩め＋強根拠必須）

**Geminiプロンプトで厳守**:
- ❌「家族で来た」「友人と」「親族で」だけでは子連れタグを付けない
- ❌「子供」「お子さん」だけも不十分（中学生以上の可能性）
- ✅ **乳幼児を示す語**または**明確な設備**が明示されている場合のみタグを付ける
- 推測禁止、根拠は evidence に必ず含める

**コード側 二重チェック**（`research_shops.py`）:
```python
# ゲート1: タグが空なら不採用
if not clean["tags"]:
    SKIP

# ゲート2: evidence に強根拠キーワードなしなら不採用
if not has_strong_evidence(clean["evidence"]):
    SKIP
```

### 強根拠キーワード（research_shops.py の STRONG_EVIDENCE_KEYWORDS）

| カテゴリ | キーワード |
|---|---|
| 乳幼児を示す語 | 赤ちゃん, ベビー, 乳児, 離乳食, おむつ, ベビーカー, 抱っこ紐, ストローラー, バウンサー, 小さい子, 未就学, 幼児, 0〜4歳, イヤイヤ期 |
| 設備・サービス | キッズチェア, 子供用椅子, ベビーチェア, ハイチェア, お子様メニュー, キッズメニュー, お子様ランチ, 子供メニュー, お子様ラーメン, おむつ替え, キッズスペース, お絵かき, おもちゃ |
| 和室系 | 座敷, お座敷, 小上がり, 小上り, 掘り炬燵, 個室 |
| ファミリー明示 | ファミレス, ファミリーレストラン |

### ④ 採用タグの厳密リスト（v2）

`ベビーカーOK` / `座敷あり` / `キッズチェアあり` / `個室あり` / `子連れOK` / `子供メニューあり` の6種のみ。

> ⚠️ 旧「騒いでもOK」タグは廃止 → 「子連れOK」に統合済み。新規追加禁止。

### ⑤ データ保護ルール

- **`id < 560` の元データ（原データ559店）は手動チェック前提のため触らない**
- **削除作業中は research_shops.py 等のバックグラウンドプロセスを必ず停止**（race conditionで戻る）
- **shops.json を直接上書きせず `merge_*.py` 経由で安全マージ**
- **API予算ガード**: Places $150/月で停止、Gemini 1,000件/日で停止、Photos 5,000件/月で停止

### ⑥ 必須メタデータ（住所・評価・営業時間）

新規追加店は **Place Details API で必ず以下を取得** して shops.json に保存：
- `address`（住所）
- `rating` / `rating_count`（Google評価・件数）
- `hours`（営業時間 weekdayDescriptions）
- `phone`（電話番号）
- `website`（公式サイト）
- `tabelog_url`（無ければ `https://www.google.com/maps/place/?q=place_id:{pid}` を自動生成）

`research_shops.py` の `fetch_reviews()` がレビューと一緒にこれらをまとめて取得し、`shops.append(entry)` 時に保存される。途中追加で抜けがあった場合は `scripts/enrich_shops_details.py` を再実行で埋まる（取得済みはスキップ）。

### ⑦ ネガティブクチコミの非表示
- `app/shop/[id]/page.tsx` の `NEGATIVE_WORDS` リストで店舗詳細ページのクチコミ表示から除外
- 該当語句: 不衛生 / うるさい / 臭い / 狭い / 汚い / まずい / 接客が悪 / 残念 / 二度と / 高い / ぼったくり 等

---

## 永続化の場所

| ファイル | 役割 |
|---|---|
| `CLAUDE.md`（このファイル） | ルール集・セッション開始時に必ず読み込み |
| `scripts/get_shops_hotpepper.py` | Hotpepperフィルタ + HP_KEYWORDS_* 定数 + has_hotpepper_kid_keyword() |
| `scripts/fetch_sapporo.py` | Google Places店名フィルタ |
| `scripts/research_shops.py` | Geminiプロンプト + STRONG_EVIDENCE_KEYWORDS + has_strong_evidence() |
| `scripts/merge_hotpepper.py` | 安全マージユーティリティ |
| `app/shop/[id]/page.tsx` | NEGATIVE_WORDS によるクチコミ表示フィルタ |

---

## 違反検知（セルフチェック）

shops.json を変更する前後に必ず以下を実行して整合性確認：

```bash
python3 -c "
import json, sys
sys.path.insert(0, 'scripts')
from get_shops_hotpepper import is_chain, has_excluded_name, EXCLUDED_GENRE_KEYWORDS_GPLACES
from research_shops import has_strong_evidence

shops = json.load(open('data/shops.json'))
violations = []
for s in shops:
    if s['id'] < 560: continue  # 原データはスキップ
    name = s['name']
    if is_chain(name) or has_excluded_name(name):
        violations.append(('name', s))
    if any(kw in name for kw in EXCLUDED_GENRE_KEYWORDS_GPLACES):
        violations.append(('genre', s))
    if not s.get('tags') or s['tags'] == ['子連れOK']:
        violations.append(('weak_tags', s))
    if s.get('source') in ('gemini','both','website') and not has_strong_evidence(s.get('evidence',[])):
        violations.append(('weak_evidence', s))
    if '騒いでもOK' in s.get('tags', []):
        violations.append(('legacy_tag', s))

print(f'違反: {len(violations)} 件')
for kind, s in violations[:5]:
    print(f'  [{kind}] [{s[\"id\"]}] {s[\"name\"]}')
"
```

違反があれば必ず修正してからコミット。

---

## インスタ自動投稿ルール（NEVER FORGET）

**現状の自動化フロー（2台のlaunchdジョブ）**

| ジョブ | 時刻 | 内容 |
|---|---|---|
| `com.bokumo.daily.plist` | 毎朝 9:00 | `run_daily.py`：3店舗抽選 → 写真取得 → 分類 → キャプション生成 → 6枚レンダリング → SSDコピー |
| `com.bokumo.post.plist` | 毎日 19:30 | `06_post_to_instagram.py`：R2アップ → IG カルーセル予約作成（**翌日19:30公開**） |

**06_post_to_instagram.py の絶対ルール**

- ✅ `scheduled_publish_time` は必須。`published=false` で予約コンテナを作る
- ✅ 投稿日時は **`next_day_epoch_at(19, 30)` で翌日19:30固定**（即時公開禁止）
- ✅ R2 アップロード先: `bokumo-instagram` バケット、キーは `{YYYYMMDD}/{shop_id}/{NN}.jpg`
- ✅ 1店舗あたり画像 **2枚以上必須**（Instagram カルーセル仕様）。2枚未満ならスキップ
- ✅ caption は `caption.txt` から読む。スクリプト側で改変しない
- ✅ `--dry-run` モードを必ず残す（R2/IG API を叩かず確認のみ）
- ✅ 失敗時は例外を握りつぶさず print して次の店へ（1店の失敗で全滅させない）
- ✅ 投稿成功時のみ `posted_history.json` に追記（`mark_posted_locally`）
- ❌ 即時 publish (`media_publish` 呼び出し) は禁止 → 24時間バッファで手動キャンセル可能にする
- ❌ FB_PAGE_TOKEN / IG_USER_ID をコードに直書き禁止、`.env.local` から読む

**run_daily.py 側のルール**

- ✅ 出力先は `outputs/instagram/{YYYYMMDD}/shop_{id}/` 配下に統一
- ✅ `processed/01.jpg〜06.jpg`（1080×1080）+ `tiktok/01.jpg〜06.jpg`（1080×1920）+ `caption.txt`
- ✅ 5番目に `05_sync_gallery.py` を実行して `data/shops.json` の `gallery` と `public/photos/gallery/` を更新
- ✅ 抽選ロジック（`01_select_shops.py`）は `posted_history.json` を見て**過去投稿済みを除外**

**トークン運用**

- `FB_PAGE_TOKEN` は無期限（Page Token）を使用。短命 User Token を直接使わない
- 万一 401/トークン切れになったら `scripts/instagram/exchange_token.py` で再発行
- `.env.local` は git 管理外、絶対にコミットしない

**launchd 操作**

```bash
launchctl list | grep bokumo                                  # 状態確認
launchctl start com.bokumo.post                               # 手動実行
launchctl unload ~/Library/LaunchAgents/com.bokumo.post.plist # 停止
launchctl load   ~/Library/LaunchAgents/com.bokumo.post.plist # 再起動
```

ログ: `~/Library/Logs/bokumo_daily.log` / `~/Library/Logs/bokumo_post.log`

---

## サイト・インフラのルール

別ドキュメント（プロジェクト初期に定めた構成ルール）に準拠：
- フレームワーク: Next.js（static export）
- ホスティング: Cloudflare Workers/Pages
- DB: Cloudflare D1（現状未使用）
- 認証: 必要時は Cloudflare Access（独自認証は実装しない）
- AIモデル: Claude Opus
- APIキー・トークンはコード直書き禁止、`.env.local` に保存
- リポジトリは Private 維持
