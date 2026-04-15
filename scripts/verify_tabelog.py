"""
data/shops.json の tabelog_url を検証する。

- 各 URL に HEAD / GET リクエストを送って生存確認
- 404 や、食べログの「店舗が見つかりません」ページへのリダイレクトを検出
- 死リンクは tabelog_url を食べログ検索URLに置き換える
  (店名 + 札幌 で検索するリンク)

使い方:
    python3 scripts/verify_tabelog.py         # 検証のみ(変更なし)
    python3 scripts/verify_tabelog.py --fix   # 死リンクを検索URLに置換して保存
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parent.parent
SHOPS_PATH = ROOT / "data" / "shops.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

SLEEP_SEC = 1.5  # 食べログへの負荷軽減


def search_url(name: str) -> str:
    """食べログの店舗検索URLを生成 (札幌エリア固定)."""
    q = parse.quote(name)
    # 北海道札幌 エリアコード A0101
    return f"https://tabelog.com/rst/rstsearch/?sa=%E6%9C%AD%E5%B9%8C&sk={q}&LstCosT_want=&Cat=RC"


def check_url(url: str) -> tuple[str, str]:
    """
    URL を検証。
    戻り値: (status, message)
      status: "ok" | "not_found" | "invalid" | "error"
    """
    if not url:
        return ("invalid", "空")
    if not url.startswith("http"):
        return ("invalid", "URLフォーマット不正")
    # 明らかにダミー(1000000000 等)
    if "100000000000" in url or "1000000000" in url:
        return ("invalid", "ダミーURL(大量の0)")

    req = request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ja,en;q=0.9",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=15) as res:
            code = res.getcode()
            final_url = res.geturl()
            body = res.read(4096).decode("utf-8", errors="ignore")
            # 食べログのトップや検索結果ページへのリダイレクトは「見つからない」扱い
            if final_url != url and "/rst/" not in final_url:
                return ("not_found", f"リダイレクト先={final_url}")
            if "店舗情報が見つかりません" in body or "お探しのお店が見つかりません" in body:
                return ("not_found", "見つかりませんページ")
            if code == 200:
                return ("ok", f"{code}")
            return ("error", f"HTTP {code}")
    except error.HTTPError as e:
        if e.code in (404, 410):
            return ("not_found", f"HTTP {e.code}")
        return ("error", f"HTTP {e.code}")
    except error.URLError as e:
        return ("error", f"接続失敗: {e.reason}")
    except Exception as e:
        return ("error", f"例外: {e}")


def main() -> None:
    fix = "--fix" in sys.argv

    shops = json.loads(SHOPS_PATH.read_text(encoding="utf-8"))
    print(f"対象: {len(shops)} 店舗")
    print(f"モード: {'修正モード(--fix)' if fix else '検証のみ'}")
    print()

    results: list[tuple[dict, str, str]] = []  # (shop, status, message)

    for i, s in enumerate(shops, 1):
        name = s.get("name", "")
        url = s.get("tabelog_url", "")
        print(f"[{i}/{len(shops)}] {name}")
        print(f"   URL: {url}")
        status, msg = check_url(url)
        print(f"   → {status.upper()} ({msg})")
        results.append((s, status, msg))
        time.sleep(SLEEP_SEC)

    ok = sum(1 for _, st, _ in results if st == "ok")
    bad = len(results) - ok

    print()
    print(f"=== 結果 ===")
    print(f"  OK : {ok} 件")
    print(f"  NG : {bad} 件")
    print()

    if bad > 0:
        print("--- NG 一覧 ---")
        for s, st, msg in results:
            if st != "ok":
                print(f"  [{st}] {s['name']} - {msg}")
        print()

    if fix and bad > 0:
        print("--- 修正: 死リンクを検索URLに置換 ---")
        for s, st, _ in results:
            if st != "ok":
                new_url = search_url(s["name"])
                print(f"  {s['name']}")
                print(f"    旧: {s.get('tabelog_url')}")
                print(f"    新: {new_url}")
                s["tabelog_url"] = new_url
        SHOPS_PATH.write_text(
            json.dumps(shops, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print()
        print(f"保存: {SHOPS_PATH}")
    elif bad > 0:
        print("ヒント: 死リンクを検索URLに自動置換するには --fix を付けて再実行してください。")


if __name__ == "__main__":
    main()
