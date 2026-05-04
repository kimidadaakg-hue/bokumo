"""今日のレンダー済み画像6枚 × 3店舗を Instagram Graph API で投稿する。

フロー:
  1. 各店の processed/01.jpg〜06.jpg を R2 にアップロード → 公開URL取得
  2. Instagram API で各画像の container 作成 (is_carousel_item=true)
  3. CAROUSEL container 作成 (children=[6つのID])
  4. media_publish で公開
  5. 投稿完了したら mark_posted.py 相当を実行

使い方:
  python3 scripts/instagram/06_post_to_instagram.py [--dry-run]
"""
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib import parse, request

import boto3

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env.local"
OUT_DIR = ROOT / "outputs" / "instagram"
HISTORY = ROOT / "logs" / "posted_history.json"

DRY_RUN = "--dry-run" in sys.argv


def load_env() -> dict:
    env = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def http_post(url: str, params: dict) -> dict:
    data = parse.urlencode(params).encode()
    req = request.Request(url, data=data, method="POST")
    with request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def http_get(url: str) -> dict:
    with request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def upload_to_r2(env: dict, local_path: Path, key: str) -> str:
    """R2 にアップロード → 公開URLを返す"""
    s3 = boto3.client(
        "s3",
        endpoint_url=env["R2_ENDPOINT"],
        aws_access_key_id=env["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    s3.upload_file(
        str(local_path),
        env["R2_BUCKET"],
        key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )
    return f"{env['R2_PUBLIC_URL']}/{key}"


def create_image_container(ig_id: str, token: str, image_url: str) -> str:
    """Instagram API: カルーセル要素 container 作成 → container_id"""
    url = f"https://graph.facebook.com/v19.0/{ig_id}/media"
    res = http_post(url, {
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": token,
    })
    if "id" not in res:
        raise RuntimeError(f"image container失敗: {res}")
    return res["id"]


def create_carousel(ig_id: str, token: str, child_ids: list, caption: str,
                    scheduled_publish_time: int | None = None) -> str:
    """CAROUSEL container 作成 → container_id

    scheduled_publish_time が指定されていれば、Instagram 側で予約投稿になる
    （10分後〜6ヶ月先までの epoch 秒）。
    """
    url = f"https://graph.facebook.com/v19.0/{ig_id}/media"
    params = {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": caption,
        "access_token": token,
    }
    if scheduled_publish_time is not None:
        params["published"] = "false"
        params["scheduled_publish_time"] = str(scheduled_publish_time)
    res = http_post(url, params)
    if "id" not in res:
        raise RuntimeError(f"carousel container失敗: {res}")
    return res["id"]


def publish(ig_id: str, token: str, container_id: str) -> dict:
    url = f"https://graph.facebook.com/v19.0/{ig_id}/media_publish"
    res = http_post(url, {
        "creation_id": container_id,
        "access_token": token,
    })
    if "id" not in res:
        raise RuntimeError(f"publish失敗: {res}")
    return res


def next_day_epoch_at(hour: int, minute: int) -> int:
    """翌日の指定時刻 (ローカル) の epoch 秒を返す"""
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=1)
    return int(target.timestamp())


def post_one_shop(env: dict, today: str, shop_id: int, shop_name: str,
                  scheduled_epoch: int) -> bool:
    shop_dir = OUT_DIR / today / f"shop_{shop_id}"
    proc_dir = shop_dir / "processed"
    caption_file = shop_dir / "caption.txt"
    if not proc_dir.exists() or not caption_file.exists():
        print(f"[{shop_id}] processed/ または caption.txt なし、スキップ")
        return False

    images = sorted(proc_dir.glob("*.jpg"))[:10]  # IGは最大10枚
    if len(images) < 2:
        print(f"[{shop_id}] 画像が2枚未満、スキップ")
        return False
    caption = caption_file.read_text(encoding="utf-8")
    schedule_str = datetime.fromtimestamp(scheduled_epoch).strftime("%Y-%m-%d %H:%M")

    print(f"\n[{shop_id}] {shop_name}: {len(images)}枚 → 予約 {schedule_str}")

    if DRY_RUN:
        for img in images:
            print(f"  (dry) {img.name}")
        print(f"  (dry) caption {len(caption)}字")
        return True

    # R2 アップロード
    image_urls = []
    for img in images:
        key = f"{today}/{shop_id}/{img.name}"
        url = upload_to_r2(env, img, key)
        image_urls.append(url)
        print(f"  ↑ {url}")

    # Instagram カルーセル作成 (予約)
    ig_id = env["IG_USER_ID"]
    token = env["FB_PAGE_TOKEN"]

    child_ids = []
    for url in image_urls:
        cid = create_image_container(ig_id, token, url)
        child_ids.append(cid)
        time.sleep(1)
    print(f"  📦 image containers: {len(child_ids)} created")

    carousel_id = create_carousel(
        ig_id, token, child_ids, caption,
        scheduled_publish_time=scheduled_epoch,
    )
    print(f"  ✅ 予約完了 (container: {carousel_id}, 公開予定: {schedule_str})")
    return True


def mark_posted_locally(shop_ids: list[int]) -> None:
    """投稿成功した店を posted_history.json に記録"""
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    posted = set(history.get("posted_shop_ids", []))
    added = []
    for sid in shop_ids:
        if sid not in posted:
            posted.add(sid)
            added.append(sid)
    history["posted_shop_ids"] = sorted(posted)
    history["last_updated"] = date.today().isoformat()
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ posted_history.json に追加: {added}")


def main() -> None:
    env = load_env()
    required = ["IG_USER_ID", "FB_PAGE_TOKEN", "R2_BUCKET", "R2_ACCESS_KEY_ID",
                "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT", "R2_PUBLIC_URL"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        raise SystemExit(f".env.local 未設定: {missing}")

    today = date.today().strftime("%Y%m%d")
    selection_file = OUT_DIR / today / "selected.json"
    if not selection_file.exists():
        raise SystemExit(f"本日の selected.json なし: {selection_file}")

    # 翌日 19:30 (ローカル) を予約時刻に
    scheduled_epoch = next_day_epoch_at(19, 30)
    schedule_str = datetime.fromtimestamp(scheduled_epoch).strftime("%Y-%m-%d %H:%M")

    selected = json.loads(selection_file.read_text(encoding="utf-8"))
    print(f"投稿対象: {len(selected)} 店 (today={today}, 公開予定: {schedule_str}, dry_run={DRY_RUN})")

    posted_ids = []
    for s in selected:
        try:
            ok = post_one_shop(env, today, s["id"], s["name"], scheduled_epoch)
            if ok and not DRY_RUN:
                posted_ids.append(s["id"])
        except Exception as e:
            print(f"  ❌ エラー: {e}")

    if posted_ids:
        mark_posted_locally(posted_ids)


if __name__ == "__main__":
    main()
