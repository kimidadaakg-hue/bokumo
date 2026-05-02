"""
ホットペッパーグルメAPI で子連れOKの飲食店を取得し
data/shops.json を生成する。

特徴:
  - child=1 パラメータで「お子様連れOK」の店のみ取得
  - 座敷・個室・ベビーカー等もAPIレスポンスから直接取得（Gemini不要）
  - 画像URLもレスポンスに含まれる（Place Photos API不要）
  - 完全無料・日次上限なし

使い方:
    export HOTPEPPER_API_KEY="your_key"
    python3 scripts/get_shops_hotpepper.py

APIキー取得:
    https://webservice.recruit.co.jp/ で無料登録
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = Path(__file__).resolve().parent / "hotpepper_fetched.json"

API_URL = "https://webservice.recruit.co.jp/hotpepper/gourmet/v1/"

# 北海道の主要エリアコード (ホットペッパー)
# https://webservice.recruit.co.jp/hotpepper/reference.html
# large_area: Z011 = 北海道
# middle_area: 個別都市
# small_area: さらに細かいエリア

# 札幌市内の middle_area コード
SAPPORO_AREAS = [
    {"code": "SA11", "name": "札幌駅・大通"},
    {"code": "SA12", "name": "すすきの"},
    {"code": "SA13", "name": "札幌市内その他"},
]

# 北海道全域でやるなら large_area=Z011 + start/count でページング
USE_ALL_HOKKAIDO = True

SLEEP_SEC = 0.3  # API負荷軽減
MAX_PER_PAGE = 100  # API上限
MAX_PAGES = 50  # 安全上限（5000店まで）

# 「中」モード: ベビーカー/キッズチェア/子供メニューが1個以上ある店だけ採用。
# 座敷・個室はファミリー判定に使わない（飲み会用のことが多いため）。
STRICT_MODE = True
QUALIFYING_TAGS = {"ベビーカーOK", "キッズチェアあり", "子供メニューあり"}

# 子連れ向きでない（または既存方針上ふさわしくない）ジャンルを除外。
# Hotpepper 側の genre.name に対する部分一致でチェック。
EXCLUDED_GENRE_KEYWORDS = ["居酒屋", "フレンチ", "イタリアン", "ダイニングバー", "バル", "ビアガーデン"]

# 店名にこれらの単語が含まれる店も除外（夜の業態が中心と推定）
EXCLUDED_NAME_KEYWORDS = [
    "ゴルフバー", "ラウンジ", "Lounge", "LOUNGE",
    "スナック", "クラブ", "CLUB",
    "BAR ", " BAR", "Bar ", " Bar", "&BAR", "&Bar",
    "バル ", " バル",
]


def has_excluded_name(name: str) -> bool:
    return any(kw in name for kw in EXCLUDED_NAME_KEYWORDS)

CHAIN_KEYWORDS = [
    "マクドナルド", "スターバックス", "スタバ", "モスバーガー",
    "ケンタッキー", "KFC", "吉野家", "すき家", "松屋",
    "サイゼリヤ", "ガスト", "デニーズ", "コメダ", "ドトール",
    "タリーズ", "プロント", "エクセルシオール", "ベローチェ",
    "バーミヤン", "ジョナサン", "ロイヤルホスト", "ココス",
    "びっくりドンキー", "ヴィクトリアステーション",
    "スシロー", "くら寿司", "かっぱ寿司", "はま寿司",
    "丸亀製麺", "はなまるうどん", "リンガーハット",
    "ミスタードーナツ", "ミスド", "サーティワン",
    "一蘭", "一風堂", "天下一品", "幸楽苑", "日高屋",
    "ワタミ", "和民", "白木屋", "鳥貴族", "磯丸",
    "ココイチ", "CoCo壱番屋",
    "サブウェイ", "バーガーキング", "ロッテリア",
    "フレッシュネス", "ファーストキッチン",
    "大戸屋", "やよい軒", "なか卯",
    "牛角", "温野菜", "しゃぶしゃぶ温野菜",
    "魚民", "白木屋", "目利きの銀次", "千年の宴",
    "笑笑", "山内農場", "豊後高田どり酒場",
    "串カツ田中", "塚田農場",
    "ペッパーランチ", "いきなりステーキ",
    "大阪王将", "餃子の王将", "日高屋",
    "鳥メロ", "ミライザカ",
    "回転寿しトリトン", "根室花まる",
    "つぼ八", "串鳥", "とんでん",
    "山頭火", "サンマルク",
    "上島珈琲",
]


def is_chain(name: str) -> bool:
    n = name.lower()
    return any(kw.lower() in n for kw in CHAIN_KEYWORDS)


def load_key() -> str:
    k = os.environ.get("HOTPEPPER_API_KEY", "").strip()
    if not k:
        print(
            "ERROR: 環境変数 HOTPEPPER_API_KEY が未設定です。\n"
            "  https://webservice.recruit.co.jp/ で無料取得できます。",
            file=sys.stderr,
        )
        sys.exit(1)
    return k


def fetch_page(api_key: str, start: int, count: int, area_code: str = "") -> dict:
    """1ページ分を取得."""
    params: dict[str, Any] = {
        "key": api_key,
        "format": "json",
        "child": 1,  # お子様連れOK
        "count": count,
        "start": start,
    }

    if USE_ALL_HOKKAIDO:
        params["large_area"] = "Z041"  # 北海道全域
    elif area_code:
        params["middle_area"] = area_code

    url = f"{API_URL}?{parse.urlencode(params)}"
    req = request.Request(url, method="GET")

    try:
        with request.urlopen(req, timeout=20) as res:
            return json.loads(res.read().decode("utf-8"))
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  [API {e.code}] {body[:200]}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"  [err] {e}", file=sys.stderr)
        return {}


def extract_tags(shop: dict) -> list[str]:
    """APIレスポンスからタグを抽出."""
    tags: list[str] = []

    # 子連れOK (child パラメータで絞ってるので基本全店)
    tags.append("子連れOK")

    # NOTE: 座敷/個室は飲み会用途が多くファミリー判定の根拠にしないため、
    # 中モードでは Hotpepper からは付与しない。

    # NOTE: barrier_free=「あり」は段差なし or 車椅子トイレなど広い意味で、
    # ベビーカーで快適に過ごせるかは別問題。誤判定が多かったため自動付与しない。
    # 店説明文に「ベビーカー」「ストローラー」と明記された場合のみ下で付与する。

    # その他の子連れ設備はフリーテキストから推定
    other_memo = shop.get("other_memo", "") or ""
    shop_detail_memo = shop.get("shop_detail_memo", "") or ""
    combined = other_memo + shop_detail_memo

    if any(kw in combined for kw in ["キッズチェア", "子供用椅子", "ベビーチェア", "ハイチェア"]):
        if "キッズチェアあり" not in tags:
            tags.append("キッズチェアあり")

    if any(kw in combined for kw in ["キッズメニュー", "お子様メニュー", "子供メニュー", "お子様ランチ"]):
        if "子供メニューあり" not in tags:
            tags.append("子供メニューあり")

    if any(kw in combined for kw in ["ベビーカー", "ストローラー"]):
        if "ベビーカーOK" not in tags:
            tags.append("ベビーカーOK")

    return tags[:6]


def detect_genre(genre_obj: dict) -> str:
    """ジャンル名を BOKUMO の5分類にマッピング."""
    name = genre_obj.get("name", "") if isinstance(genre_obj, dict) else str(genre_obj)
    n = name.lower()

    if any(kw in n for kw in ["カフェ", "喫茶", "スイーツ", "パン", "ケーキ"]):
        return "カフェ"
    if any(kw in n for kw in ["和食", "日本料理", "寿司", "蕎麦", "うどん", "天ぷら",
                                "焼鳥", "居酒屋", "割烹", "懐石", "おでん", "鍋",
                                "焼肉", "もつ", "しゃぶ", "すき焼"]):
        return "和食"
    if any(kw in n for kw in ["イタリアン", "イタリア", "パスタ", "ピザ", "ピッツァ"]):
        return "イタリアン"
    if any(kw in n for kw in ["フレンチ", "フランス", "洋食", "ステーキ", "ハンバーグ",
                                "欧風", "ビストロ"]):
        return "洋食"
    return "その他"


def detect_area(address: str) -> str:
    """住所から大まかなエリアを判定."""
    if "宮の森" in address or "宮ケ丘" in address:
        return "宮の森"
    if "円山" in address:
        return "円山"
    # 北海道の都市名を抽出
    cities = [
        "旭川", "函館", "釧路", "帯広", "北見", "苫小牧",
        "室蘭", "岩見沢", "小樽", "江別", "千歳", "恵庭",
        "石狩", "北広島", "登別", "伊達", "網走", "稚内",
        "紋別", "名寄", "富良野", "美瑛", "留萌", "根室",
        "滝川", "砂川", "深川", "士別", "芦別",
    ]
    for city in cities:
        if city in address:
            return city

    if "札幌" in address:
        # 区名を抜き出し
        for ku in ["中央区", "北区", "東区", "白石区", "厚別区",
                    "豊平区", "清田区", "南区", "西区", "手稲区"]:
            if ku in address:
                return f"札幌{ku}"
        return "札幌"

    return "北海道"


def calc_score(shop: dict, tags: list[str]) -> int:
    """タグの充実度からスコアを計算."""
    score = 3  # base (子連れOK は確定)
    bonus_tags = {"座敷あり", "個室あり", "ベビーカーOK", "キッズチェアあり", "子供メニューあり"}
    count = len(set(tags) & bonus_tags)
    if count >= 3:
        score = 5
    elif count >= 1:
        score = 4
    return score


def normalize(shop: dict, idx: int) -> dict:
    """ホットペッパーのレスポンスを BOKUMO 形式に変換."""
    genre_obj = shop.get("genre", {})
    tags = extract_tags(shop)
    address = shop.get("address", "")

    # 画像URL (ホットペッパーは l / m / s サイズを提供)
    photo = shop.get("photo", {}) or {}
    image_url = (
        photo.get("pc", {}).get("l", "")
        or photo.get("mobile", {}).get("l", "")
        or ""
    )

    # Google Maps リンク生成
    name = shop.get("name", "")
    lat = shop.get("lat", 0)
    lng = shop.get("lng", 0)
    maps_url = (
        f"https://www.google.com/maps/search/?api=1"
        f"&query={parse.quote(name)}"
        f"&query={parse.quote(address)}"
    )

    return {
        "id": idx,
        "name": name,
        "area": detect_area(address),
        "genre": detect_genre(genre_obj),
        "tags": tags,
        "description": (shop.get("catch", "") or "")[:50] or (shop.get("genre_catch", "") or "")[:50],
        "score": calc_score(shop, tags),
        "lat": float(lat) if lat else 0,
        "lng": float(lng) if lng else 0,
        "tabelog_url": maps_url,
        "image_url": image_url,
        "is_chain": False,
        "hotpepper_id": shop.get("id", ""),
        "address": address,
        "open": shop.get("open", ""),
        "hotpepper_url": (shop.get("urls", {}) or {}).get("pc", ""),
    }


def main() -> None:
    api_key = load_key()

    print("=" * 50)
    print("BOKUMO get_shops_hotpepper.py")
    print("=" * 50)
    print(f"対象: {'北海道全域' if USE_ALL_HOKKAIDO else '札幌市内'}")
    print(f"フィルタ: child=1 (お子様連れOK)")
    print()

    all_shops: list[dict] = []
    total_available = 0
    page = 1

    while page <= MAX_PAGES:
        start = (page - 1) * MAX_PER_PAGE + 1
        print(f"[page {page}] start={start} ...", end=" ", flush=True)

        data = fetch_page(api_key, start, MAX_PER_PAGE)
        results = data.get("results", {})
        total_available = int(results.get("results_available", 0))
        returned = int(results.get("results_returned", 0))
        shops_list = results.get("shop", []) or []

        print(f"取得: {returned} / 全{total_available}")

        all_shops.extend(shops_list)

        if start + returned > total_available:
            break
        page += 1
        time.sleep(SLEEP_SEC)

    print()
    print(f"取得合計: {len(all_shops)} 件 (API上の該当: {total_available})")

    # 重複除外 (hotpepper id ベース)
    seen: set[str] = set()
    unique: list[dict] = []
    for s in all_shops:
        sid = s.get("id", "")
        if sid in seen:
            continue
        seen.add(sid)
        unique.append(s)
    print(f"重複除去後: {len(unique)} 件")

    # チェーン店除外
    chain_count = 0
    non_chain: list[dict] = []
    for s in unique:
        name = s.get("name", "")
        if is_chain(name):
            chain_count += 1
        else:
            non_chain.append(s)
    print(f"チェーン除外: {chain_count} 件")
    print(f"非チェーン: {len(non_chain)} 件")

    # ジャンル除外（居酒屋/フレンチ/イタリアン等）
    excluded_genre_count = 0
    after_genre: list[dict] = []
    for s in non_chain:
        gname = (s.get("genre", {}) or {}).get("name", "")
        if any(kw in gname for kw in EXCLUDED_GENRE_KEYWORDS):
            excluded_genre_count += 1
        else:
            after_genre.append(s)
    print(f"ジャンル除外({','.join(EXCLUDED_GENRE_KEYWORDS)}): {excluded_genre_count} 件")
    print(f"残り: {len(after_genre)} 件")

    # 店名NG（バー/ラウンジ/スナック等）
    excluded_name_count = 0
    after_name: list[dict] = []
    for s in after_genre:
        if has_excluded_name(s.get("name", "")):
            excluded_name_count += 1
        else:
            after_name.append(s)
    print(f"店名NG除外: {excluded_name_count} 件")
    print(f"残り: {len(after_name)} 件")
    after_genre = after_name

    # 変換
    shops = []
    for i, s in enumerate(after_genre, 1):
        shops.append(normalize(s, i))

    # 「中」モード: 子連れ要素タグが1個以上ある店だけ採用
    if STRICT_MODE:
        before = len(shops)
        shops = [
            s for s in shops
            if any(t in QUALIFYING_TAGS for t in s["tags"])
        ]
        print(f"中モード絞り込み(qualifying tag必須): {before} → {len(shops)} 件")

    # 保存
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(shops, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # レポート
    from collections import Counter
    area_c = Counter(s["area"] for s in shops)
    genre_c = Counter(s["genre"] for s in shops)
    score_c = Counter(s["score"] for s in shops)
    tag_c: Counter[str] = Counter()
    for s in shops:
        for t in s["tags"]:
            tag_c[t] += 1

    print()
    print("=" * 50)
    print("処理結果")
    print("=" * 50)
    print(f"  登録: {len(shops)} 件")
    print()
    print("エリア別:")
    for a, c in area_c.most_common(20):
        print(f"  {a}: {c}")
    print()
    print("ジャンル別:")
    for g, c in genre_c.most_common():
        print(f"  {g}: {c}")
    print()
    print("スコア別:")
    for sc in sorted(score_c.keys(), reverse=True):
        print(f"  ★{sc}: {score_c[sc]}")
    print()
    print("タグ別:")
    for t, c in tag_c.most_common():
        print(f"  {t}: {c}")
    print()
    print(f"出力: {OUT_PATH}")


if __name__ == "__main__":
    main()
