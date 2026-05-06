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

### ⑧ area の自動推定ルール（2026-05-05 円山誤分類事故対応・絶対遵守）

**過去事故**: 旧 `research_shops.py` に `"area": "宮の森" if ... else "円山"` のハードコードが残っており、
札幌10区で集めた店も道内他市の店も全て area="円山" と誤分類されていた。被害190店、サイトの地域フィルタが完全に嘘になっていた。

**永続ルール**:
- ❌ 新規パイプラインで `area` をハードコード（固定値）しない
- ✅ 必ず `research_shops.py` の `area_from_address(address)` を使う
- ✅ area_from_address は住所から「札幌○○区」「函館」「旭川」などを正規表現で抽出
- ✅ 「円山」「宮の森」など中央区の細分化エリアは住所キーワードで個別上書き
- 北海道外の住所（住所に「北海道」を含まない）は area="不明" を返す → 取り込み時に弾く

**area_from_address の正規表現で過去にハマった点（2026-05-06 まで）**:
- ❌ greedy `[^...]+市` で「北海道釧路市」全体マッチ → 「北海道釧路」になる事故
  → 必ず `北海道\s*([^...]+?市)` のように「北海道」を剥がしてから lazy `+?` で抽出
- ❌ char class から「北」を除外する小手先の修正 → 「北見市」「北広島市」がマッチしなくなる
  → char class を絞らず、「北海道」プレフィックスで境界を作る方が安全
- ❌ 「町」を裸で抽出 → 「本町」「東町」のような町名と衝突
  → 必ず「○○郡△△町」のセットで採用

**新規データ追加後のチェック**（必ず実行）:
1. CLAUDE.md セルフチェックスクリプト（前述）で違反0件
2. `Counter(s['area'] for s in shops).most_common(20)` で地域分布確認
   → 1地域が異常に多い（円山192店のような状況）= バグまたはデータ汚染の兆候
3. `[s for s in shops if '北海道' not in s.get('address','')]` で道外混入チェック
   → 過去に「白石区/白石市」名前衝突で宮城県の店が混入した実績あり
4. `git diff data/shops.json` で area 変更が想定範囲内か視覚的に確認

### ⑨ 候補発掘キーワードの設計（2026-05-05 整備）

`scripts/fetch_hokkaido.py` には Text Search に使うキーワードが **2 種類** ある。
両方を併用するのが標準（`--keywords all` がデフォルト）。

**1. `GENRE_KEYWORDS`（18個・料理ジャンル中立）**
カフェ / ファミリーレストラン / ラーメン / うどん 蕎麦 / 回転寿司 / 焼肉 / とんかつ /
中華料理 / ハンバーグ / パン屋 / 寿司 / 海鮮 / 定食 / 洋食 / パスタ / お好み焼き /
スイーツ / カレー
- 中立な料理ジャンルで網羅的に拾う。Gemini 通過率は約 **13%**
- 「子連れ判定は Gemini に任せる」発想

**2. `KIDS_FOCUS_KEYWORDS`（7個・子連れ前提）**
子連れ ランチ / キッズメニュー / ファミリー / 子連れ カフェ / お子様メニュー /
個室 子連れ / 座敷 ランチ
- Google の Text Search が「子連れ」「キッズ」を含むクチコミ・サイトを持つ店を上位に返す
- Gemini 通過率は **30〜50%** 期待（料理ジャンル中立の3〜4倍）

**`--keywords` の使い分けルール**:
- **新規エリア**（過去に一度もリサーチしてない地域）は `--keywords all`（25個全部）
- **既存リサーチ済みエリア**（札幌など）は `--keywords kids` のみ
  → ジャンル分は重複だらけになるので、子連れ前提だけ叩いて取りこぼし回収
- `--keywords genre` は基本使わない（後方互換用）

**禁止事項**:
- 居酒屋 / バー / バル / クラブ など夜業態を示すキーワードは追加しない
- ベーカリー / パンケーキ は「パン屋」「スイーツ」と被るので追加しない
- 個別店名（「マクドナルド」等）でクエリを作らない

### ⑩ 非飲食店の混入防止（2026-05-05 強化）

子連れ前提キーワード（「ファミリー」「子連れ」等）で Text Search すると、Google が
**保育園・児童会館・クリニック・公園施設** など飲食店ではない場所も返してくる。
過去に [2327]保育園キッズプラス / [2329]札幌市中島児童会館 / [2364]こどもクリニック
が混入した実績あり。

**永続ルール**:
- ✅ `research_shops.py` の `is_food_place(types)` で Place Type をチェック
- ✅ 飲食店系 type（`restaurant` / `cafe` / `bakery` / `meal_takeaway` / `meal_delivery` / `food` / `*_restaurant`）を1つでも含めば採用、そうでなければ SKIP
- ✅ 2段階フィルタ:
  1. `shops_raw.json` の raw 段階で types がある場合 → Place Details を叩く前に SKIP（コスト$0）
  2. raw に無い場合 → Place Details 取得後の types で最終確認 → Gemini を叩く前に SKIP

**新規データ追加後の追加チェック**（必ず実行）:
- 怪しい店名キーワードでスキャン: `保育園 / 幼稚園 / 学校 / 病院 / クリニック / 児童会館 / 図書館 / 公園 / ホテル / 美容室 / 神社 / 寺 / 駅(※駅前店は除外) / 役所` 等
- ヒットした店を目視確認、非飲食店は削除

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

**現状の自動化フロー（3台のlaunchdジョブ）**

| ジョブ | 時刻 | 内容 |
|---|---|---|
| `com.bokumo.research.plist` | 毎朝 4:00 | `research_shops.py`：Gemini 1日1000件まで判定 → shops.json 追加。未処理0件なら即終了（課金 $0） |
| `com.bokumo.daily.plist` | 毎朝 9:00 | `run_daily.py`：3店舗抽選 → 写真取得 → 分類 → キャプション生成 → 6枚レンダリング → SSDコピー |
| `com.bokumo.post.plist` | 毎日 19:30 | `06_post_to_instagram.py`：R2アップ → IG カルーセル作成 → **即時公開** |

**Meta API 制約（重要・2026-05-04 判明）**
- `scheduled_publish_time` を使った予約投稿は **Meta のコンテンツ公開ホワイトリスト承認済みアカウント限定**。一般アカウントが叩くと `(#3) User must be on whitelist` で 400 エラー
- そのため本プロジェクトでは **即時公開のみ** サポート。予約は使わない
- 投稿前に問題があれば 19:30 ジョブを止めるか、公開後に Instagram から削除して対応

**06_post_to_instagram.py の絶対ルール**

- ✅ 各画像コンテナを作成後、`status_code=FINISHED` になるまで `wait_container_ready()` でポーリング
- ✅ CAROUSEL コンテナ作成 → `media_publish` で即時公開（19:30 のジョブ実行時点で公開）
- ✅ R2 アップロード先: `bokumo-instagram` バケット、キーは `{YYYYMMDD}/{shop_id}/{NN}.jpg`
- ✅ 1店舗あたり画像 **2枚以上必須**（Instagram カルーセル仕様）。2枚未満ならスキップ
- ✅ caption は `caption.txt` から読む。スクリプト側で改変しない
- ✅ `--dry-run` モードを必ず残す（R2/IG API を叩かず確認のみ）
- ✅ 失敗時は例外を握りつぶさず print して次の店へ（1店の失敗で全滅させない）
- ✅ HTTPError は必ずレスポンスボディを `RuntimeError` に含める（Meta API のエラー詳細が消えないように）
- ✅ 投稿成功時のみ `posted_history.json` に追記（`mark_posted_locally`）
- ❌ `scheduled_publish_time` / `published=false` を使った予約投稿は禁止（ホワイトリスト未承認のため不可）
- ❌ FB_PAGE_TOKEN / IG_USER_ID をコードに直書き禁止、`.env.local` から読む

**spam 判定回避の3段安全装置（2026-05-06 追加）**

過去事故: トークン権限切れ＋手動リカバリで同じ画像を短時間に何度もアップして
Meta から「Application request limit reached」で 24h ブロックされた。

| # | 安全装置 | 動作 | 効果 |
|---|---|---|---|
| 1 | **`verify_token()` プリフライト** | 投稿開始前に `GET /me?access_token=` で検証。失敗なら起動しない | 権限切れトークンで18個の無駄コンテナを作る事故を回避 |
| 2 | **フェイルファスト** | 1店目失敗かつ posted_ids が空なら残り全店スキップ | 同じ問題で連鎖的に全店分のコンテナを作る spam 化を回避 |
| 3 | **`failed_attempts.json` 同日リトライ禁止** | 失敗した shop_id を `logs/failed_attempts.json` の今日の配列に記録、同日中の再試行をスキップ | 手動リカバリで同じ画像を再投稿して spam 判定される事故を回避 |

`failed_attempts.json` の構造:
```json
{
  "20260506": [272, 2313, 261]
}
```
日付キーが今日かどうかで判定 → 翌日になると自動的にリセットされる挙動。手動でリセットしたい時はファイル削除 or 該当キー削除。

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
launchctl list | grep bokumo                                      # 状態確認
launchctl start com.bokumo.post                                   # 手動実行
launchctl unload ~/Library/LaunchAgents/com.bokumo.post.plist     # 停止
launchctl load   ~/Library/LaunchAgents/com.bokumo.post.plist     # 再起動
launchctl unload ~/Library/LaunchAgents/com.bokumo.research.plist # researchジョブ停止
```

ログ: `~/Library/Logs/bokumo_daily.log` / `~/Library/Logs/bokumo_post.log` / `~/Library/Logs/bokumo_research.log`

**研究ジョブ（com.bokumo.research）について**:
- 毎朝 4:00 に `bokumo_research.sh` 経由で `research_shops.py` を1回実行
- Gemini 1日1000件上限で自動停止（=> 約1〜2時間で完了）
- 未処理候補が0件なら API を叩かず即終了（課金 $0）
- 新規ロットを `fetch_hokkaido.py` で発掘すれば、翌朝から自動的に処理再開
- 完全停止したいときは `launchctl unload` で外す

---

## Instagram スライド1（カバー画像）デザイン確定仕様（2026-05-06）

**サイズ・レイアウト**:
- 1080×1350 (4:5 縦長、Instagram プロフィールグリッド最適)
- 写真ベタ表示（半透明ダーク帯は使わない、写真の主役感を最大化）
- テキストは写真上に直接配置、白フィル + 縁取りで視認性確保

**4つのテキスト要素の配置**:
1. **左上: 縦書きで地名（極大）** — 写真と並ぶメインビジュアル要素
2. **右上: 「BOKUMO」+ サブ2行** — 雑誌風ブランドヘッダー
3. **下部: キャッチコピー「子連れに優しいお店」（極大、ベージュ）** — 唯一のアクセントカラー
4. **下部下: 設備タグ（ピンク✓付き）** — 機能訴求

**地名表示ルール（厳守）**:
- `area` フィールドの値を **そのまま** 使う（micro レベル維持）
  - ❌ サブエリアへ集約（札幌中央区→中央区、旭川駅周辺→旭川 等）はしない
  - ✅ 「中島公園・山鼻」「函館ベイエリア」「旭川駅周辺」等 micro 値を維持
- 「・」は縦書き向けに「︙」（縦中点）に自動変換
- 文字数別フォントサイズ（`vertical_area_size()`）:
  - 1-2字: 270pt / 3字: 230pt / 4字: 195pt
  - 5字: 170pt / 6字: 145pt / 7+字: 125pt
- ストローク幅は `size // 35`（サイズ連動）

**フォント**:
- 縦書き地名・キャッチ・タグ: **Mochiy Pop One**（`FONT_BRUSH`、丸くてポップな手書き風）
- BOKUMO・サブ・他スライド: **Klee One SemiBold**（教科書風、英字も可読）

**色（厳守）**:
- `WHITE = (255, 255, 255)` — 文字メイン色
- `BEIGE = (245, 222, 179)` — **キャッチコピー「子連れに優しいお店」専用**（唯一のアクセント）
- `STROKE_DARK = (160, 125, 95)` — 縁取り（明るめのベージュブラウン、黒禁止）
- `PINK = (224, 91, 124)` — ✓バッジ専用

**禁止事項**:
- ❌ 半透明ダーク帯（写真が見えにくくなる）
- ❌ 真っ黒の縁取り（硬すぎる、温かみが消える）
- ❌ ハート ♡ 文字（Mochiy Pop One に未収録のため、置換せず削除済み）
- ❌ 店名を slide1 に表示（slide2 で表示するので重複させない）
- ❌ エリア・ジャンルを slide1 に表示（slide2 の情報パネルに移動済み）

仕様変更したい場合は、コミット前に必ずユーザー確認を取ること。

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
