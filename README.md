# BOKUMO

**「僕も連れてって、が叶うお店」** — 札幌市・円山 / 宮の森エリアの子連れ歓迎飲食店まとめサイト。

## 技術スタック

- Next.js 14 (App Router)
- TypeScript
- TailwindCSS
- Google Maps JavaScript API (`@react-google-maps/api`)
- データ: ローカル JSON (`/data/shops.json`)

## フォルダ構成

```
bokumo/
├── app/
│   ├── globals.css        # Tailwind 読み込み + 基本スタイル
│   ├── layout.tsx         # 全体レイアウト / メタ情報
│   └── page.tsx           # トップページ (一覧 + 地図)
├── components/
│   ├── FilterBar.tsx      # ジャンル・タグフィルター
│   ├── Map.tsx            # Google Maps (ピン + InfoWindow)
│   └── ShopCard.tsx       # 店舗カード UI
├── data/
│   └── shops.json         # ダミー店舗データ (10件)
├── types/
│   └── shop.ts            # Shop 型 / タグ定数
├── public/
├── .env.local.example
├── next.config.js
├── package.json
├── postcss.config.js
├── tailwind.config.ts
└── tsconfig.json
```

## セットアップ手順（初心者向け）

### 1. Node.js をインストール
[https://nodejs.org/](https://nodejs.org/) から LTS 版（18 以上）をインストールしてください。

### 2. プロジェクトに移動して依存をインストール
ターミナルを開いて:

```bash
cd bokumo
npm install
```

### 3. Google Maps API キーを用意

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 「APIとサービス」→「ライブラリ」で **Maps JavaScript API** を有効化
3. 「認証情報」→「認証情報を作成」→ API キー
4. （推奨）API キーに HTTP リファラー制限をかける

### 4. 環境変数ファイルを作成

```bash
cp .env.local.example .env.local
```

`.env.local` を開いて、取得したキーを貼り付け:

```
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=ここにAPIキー
```

### 5. 開発サーバー起動

```bash
npm run dev
```

ブラウザで [http://localhost:3000](http://localhost:3000) を開くと BOKUMO が表示されます。

### 6. 本番ビルド

```bash
npm run build
npm start
```

## 機能

- **店舗カード一覧**：画像 / 店名 / ジャンル / タグ / 説明 / 子連れ安心度スコア（★）/ 食べログリンク
- **フィルター**：ジャンル（カフェ / 和食 / 洋食 / イタリアン / その他）＋ タグ複数選択
  - ベビーカーOK / 座敷あり / キッズチェアあり / 個室あり / 騒いでもOK / 子供メニューあり
- **地図連動**：ピンクリック → 該当カードへスクロール、カードホバー → ピンがハイライト
- **レスポンシブ**：スマホでは地図が下に回り込む
- **ホバーアニメーション**：カードがふわっと浮く

## 店舗データの編集

`data/shops.json` を書き換えるだけで反映されます。緯度経度は Google マップで右クリック→座標をコピー、が簡単です。
