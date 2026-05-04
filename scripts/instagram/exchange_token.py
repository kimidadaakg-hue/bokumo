"""短期 User Access Token を長期トークン (60日) に変換し、
さらに Page Access Token (実質無期限) を取得して .env.local に書き戻す。

実行前: .env.local に以下を記入しておく
  META_APP_ID
  META_APP_SECRET
  FB_USER_TOKEN_SHORT
  FB_PAGE_ID
  IG_USER_ID
"""
import json
import sys
from pathlib import Path
from urllib import request, parse

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env.local"


def load_env() -> dict:
    env = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def save_env(env: dict) -> None:
    """既存ファイルのキーを更新、新キーは末尾に追加"""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    keys_seen = set()
    out = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in env:
                out.append(f"{k}={env[k]}")
                keys_seen.add(k)
                continue
        out.append(line)
    for k, v in env.items():
        if k not in keys_seen:
            out.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")


def http_get(url: str) -> dict:
    with request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    env = load_env()
    required = ["META_APP_ID", "META_APP_SECRET", "FB_USER_TOKEN_SHORT", "FB_PAGE_ID", "IG_USER_ID"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        raise SystemExit(f".env.local に以下が未設定: {missing}")

    print("1) 短期 User Token → 長期 User Token (60日) に変換")
    url = (
        f"https://graph.facebook.com/v19.0/oauth/access_token?"
        f"grant_type=fb_exchange_token&client_id={env['META_APP_ID']}&"
        f"client_secret={env['META_APP_SECRET']}&"
        f"fb_exchange_token={env['FB_USER_TOKEN_SHORT']}"
    )
    res = http_get(url)
    long_user_token = res.get("access_token")
    if not long_user_token:
        raise SystemExit(f"長期User Token取得失敗: {res}")
    print(f"   ✅ 長期User Token取得 (有効期限約60日)")

    print("2) 長期 User Token → 長期 Page Token (実質無期限)")
    url = (
        f"https://graph.facebook.com/v19.0/{env['FB_PAGE_ID']}?"
        f"fields=access_token&access_token={long_user_token}"
    )
    res = http_get(url)
    long_page_token = res.get("access_token")
    if not long_page_token:
        raise SystemExit(f"Page Token取得失敗: {res}")
    print(f"   ✅ 長期Page Token取得 (有効期限なし)")

    # 保存
    env["FB_USER_TOKEN_LONG"] = long_user_token
    env["FB_PAGE_TOKEN"] = long_page_token
    save_env(env)
    print()
    print(f"✅ .env.local に保存:")
    print(f"   FB_USER_TOKEN_LONG={long_user_token[:20]}... (60日有効)")
    print(f"   FB_PAGE_TOKEN={long_page_token[:20]}... (無期限)")
    print()
    print("以降は FB_PAGE_TOKEN を投稿時に使う")


if __name__ == "__main__":
    main()
