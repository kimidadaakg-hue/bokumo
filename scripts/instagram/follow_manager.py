"""BOKUMO Instagram フォロー履歴管理 + アンフォロー候補リスト出力。

Instagram Graph API は他人のフォロー操作に対応していないため、フォロー自体は手動。
このスクリプトは「履歴の記録」と「アンフォロー候補リストアップ」だけを行う。

フロー:
  1. ユーザーが手動で IG アプリから20件フォロー
  2. add コマンドで履歴記録: python3 follow_manager.py add @username [--source @seed_account] [--note "..."]
  3. 7日後、 candidates コマンドで「フォロー返ししない人」リスト確認
  4. ユーザーが手動でアンフォロー
  5. unfollow コマンドで履歴から削除: python3 follow_manager.py unfollow @username
  6. フォロー返してくれた人は reciprocated コマンドで印付け: python3 follow_manager.py reciprocated @username

履歴ファイル:
  logs/instagram_follows.json
  {
    "follows": [
      {
        "username": "@example",
        "followed_date": "2026-05-07",
        "source": "@kushio181011",
        "category": "札幌ママ",
        "note": "投稿頻度高め",
        "reciprocated": false,
        "reciprocated_date": null,
        "unfollowed": false,
        "unfollowed_date": null
      }
    ]
  }
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "logs" / "instagram_follows.json"

DEFAULT_UNFOLLOW_AFTER_DAYS = 7  # フォロー返しなしの店をアンフォロー候補にする日数


def load_history() -> dict:
    if HISTORY.exists():
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    return {"follows": []}


def save_history(data: dict) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_username(name: str) -> str:
    """先頭の @ を統一する."""
    name = name.strip()
    if not name.startswith("@"):
        name = "@" + name
    return name


def cmd_add(args) -> None:
    """フォロー記録を追加."""
    username = normalize_username(args.username)
    data = load_history()
    # 重複チェック
    for f in data["follows"]:
        if f["username"] == username and not f.get("unfollowed"):
            print(f"⚠️  既に履歴あり: {username} (followed_date={f['followed_date']})")
            return
    entry = {
        "username": username,
        "followed_date": date.today().isoformat(),
        "source": args.source or "",
        "category": args.category or "子育てママ",
        "note": args.note or "",
        "reciprocated": False,
        "reciprocated_date": None,
        "unfollowed": False,
        "unfollowed_date": None,
    }
    data["follows"].append(entry)
    save_history(data)
    print(f"✅ 追加: {username} (source={entry['source']}, today={entry['followed_date']})")
    active_count = sum(1 for f in data["follows"] if not f.get("unfollowed"))
    print(f"   累計アクティブフォロー: {active_count}")


def cmd_reciprocated(args) -> None:
    """相互フォロー成立印を付ける."""
    username = normalize_username(args.username)
    data = load_history()
    for f in data["follows"]:
        if f["username"] == username and not f.get("unfollowed"):
            f["reciprocated"] = True
            f["reciprocated_date"] = date.today().isoformat()
            save_history(data)
            print(f"✅ 相互フォロー記録: {username}")
            return
    print(f"❌ 履歴に見つからず: {username}")


def cmd_unfollow(args) -> None:
    """アンフォロー記録を付ける."""
    username = normalize_username(args.username)
    data = load_history()
    for f in data["follows"]:
        if f["username"] == username and not f.get("unfollowed"):
            f["unfollowed"] = True
            f["unfollowed_date"] = date.today().isoformat()
            save_history(data)
            print(f"✅ アンフォロー記録: {username}")
            return
    print(f"❌ アクティブな履歴に見つからず: {username}")


def cmd_candidates(args) -> None:
    """アンフォロー候補リスト（N日経過 & 相互フォローなし）."""
    days = args.days or DEFAULT_UNFOLLOW_AFTER_DAYS
    cutoff = date.today() - timedelta(days=days)
    data = load_history()
    candidates = []
    for f in data["follows"]:
        if f.get("unfollowed"):
            continue
        if f.get("reciprocated"):
            continue
        followed = date.fromisoformat(f["followed_date"])
        if followed <= cutoff:
            elapsed = (date.today() - followed).days
            candidates.append((elapsed, f))
    candidates.sort(key=lambda x: -x[0])
    print(f"=== アンフォロー候補（{days}日以上経過 & フォロー返しなし）===")
    if not candidates:
        print("（候補なし）")
        return
    for elapsed, f in candidates:
        print(f"  {elapsed:3d}日経過 {f['username']:30s} (source={f['source']})")
        if f.get("note"):
            print(f"           note: {f['note']}")
    print()
    print(f"合計: {len(candidates)} 件")
    print()
    print("→ ユーザーが Instagram で手動アンフォロー後、以下を順次実行:")
    for _, f in candidates[:5]:
        print(f"   python3 scripts/instagram/follow_manager.py unfollow {f['username']}")


def cmd_status(args) -> None:
    """現在の状況サマリ."""
    data = load_history()
    total = len(data["follows"])
    active = [f for f in data["follows"] if not f.get("unfollowed")]
    reciprocated = [f for f in active if f.get("reciprocated")]
    today_str = date.today().isoformat()
    today_added = [f for f in data["follows"] if f.get("followed_date") == today_str]

    print("=== BOKUMO Instagram フォロー履歴 ===")
    print(f"全期間総フォロー数: {total}")
    print(f"  - 今もフォロー中: {len(active)}")
    print(f"  - 相互フォロー成立: {len(reciprocated)} ({len(reciprocated)*100//max(len(active),1)}%)")
    print(f"  - アンフォロー済: {total - len(active)}")
    print(f"今日新規フォロー: {len(today_added)} / 20 (1日目標)")
    if len(today_added) >= 20:
        print("  🎉 今日のノルマ達成")
    print()
    # source 別
    from collections import Counter
    sources = Counter(f.get("source", "") for f in active)
    print("source 別アクティブ数:")
    for src, n in sources.most_common(10):
        print(f"  {src or '(未指定)':30s} {n}")


def cmd_list(args) -> None:
    """全アクティブフォローを表示."""
    data = load_history()
    active = [f for f in data["follows"] if not f.get("unfollowed")]
    print(f"=== アクティブフォロー {len(active)} 件 ===")
    for f in sorted(active, key=lambda x: x["followed_date"]):
        mark = "✓" if f.get("reciprocated") else " "
        print(f"  [{mark}] {f['followed_date']} {f['username']:30s} {f.get('source','')}")


def main() -> None:
    ap = argparse.ArgumentParser(description="BOKUMO Instagram フォロー履歴管理")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="フォロー記録追加")
    p_add.add_argument("username", help="フォローしたユーザー名（@有り無しどちらでもOK）")
    p_add.add_argument("--source", help="どの種アカウントのフォロワーから見つけたか")
    p_add.add_argument("--category", default="子育てママ", help="カテゴリ")
    p_add.add_argument("--note", help="メモ")

    p_recip = sub.add_parser("reciprocated", help="相互フォロー印")
    p_recip.add_argument("username")

    p_unf = sub.add_parser("unfollow", help="アンフォロー記録")
    p_unf.add_argument("username")

    p_cand = sub.add_parser("candidates", help="アンフォロー候補リスト")
    p_cand.add_argument("--days", type=int, help=f"経過日数（デフォルト{DEFAULT_UNFOLLOW_AFTER_DAYS}）")

    sub.add_parser("status", help="現在の状況サマリ")
    sub.add_parser("list", help="全アクティブフォロー一覧")

    args = ap.parse_args()
    {
        "add": cmd_add,
        "reciprocated": cmd_reciprocated,
        "unfollow": cmd_unfollow,
        "candidates": cmd_candidates,
        "status": cmd_status,
        "list": cmd_list,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
