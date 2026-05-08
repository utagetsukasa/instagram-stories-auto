import os
import json
import sys
import time
import requests
import jpholiday
from datetime import date, datetime, timedelta, timezone

CLOSURES_FILE = "closures.json"
ANNOUNCEMENTS_FILE = "announcements.json"


def load_closures():
    if not os.path.exists(CLOSURES_FILE):
        return []
    with open(CLOSURES_FILE, "r") as f:
        data = json.load(f)
    return [date.fromisoformat(d) for d in data.get("closures", [])]


def load_announcements_for(target_date):
    """target_date が start〜end 範囲内の announcement を返す（両端含む）"""
    if not os.path.exists(ANNOUNCEMENTS_FILE):
        return []
    with open(ANNOUNCEMENTS_FILE, "r") as f:
        data = json.load(f)
    result = []
    for ann in data.get("announcements", []):
        start = date.fromisoformat(ann["start"])
        end = date.fromisoformat(ann["end"])
        if start <= target_date <= end:
            result.append(ann)
    return result


def get_today_image():
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).date()
    if jpholiday.is_holiday(today):
        return "holiday.png"
    day_map = {
        0: "monday.png",
        1: "tuesday.png",
        2: "wednesday.png",
        3: "thursday.png",
        4: "friday.png",
        5: "saturday.png",
        6: "sunday.png",
    }
    return day_map[today.weekday()]


def raise_for_status_with_body(response):
    """raise_for_status と同様だが、エラー時にレスポンス本文も表示する。"""
    if not response.ok:
        print(f"[ERROR] HTTP {response.status_code}: {response.text}", file=sys.stderr)
        response.raise_for_status()


def post_image_story(image_filename, user_id, access_token, repo):
    image_url = f"https://raw.githubusercontent.com/{repo}/main/{image_filename}"
    create_url = f"https://graph.instagram.com/v21.0/{user_id}/media"
    create_params = {
        "image_url": image_url,
        "media_type": "STORIES",
        "access_token": access_token,
    }
    print(f"[DEBUG] メディアコンテナ作成中: {image_url}")
    response = requests.post(create_url, params=create_params)
    raise_for_status_with_body(response)
    creation_id = response.json()["id"]
    print(f"[DEBUG] コンテナ作成完了: creation_id={creation_id}")

    # 画像の処理完了を待機
    for attempt in range(12):
        status_url = f"https://graph.instagram.com/v21.0/{creation_id}"
        status_params = {
            "fields": "status_code",
            "access_token": access_token,
        }
        status_resp = requests.get(status_url, params=status_params)
        raise_for_status_with_body(status_resp)
        status_code = status_resp.json().get("status_code")
        if status_code == "FINISHED":
            break
        elif status_code == "ERROR":
            raise RuntimeError(f"画像処理エラー: {image_filename}")
        print(f"画像処理中... ({attempt + 1}/12)")
        time.sleep(10)
    else:
        raise TimeoutError(f"画像処理タイムアウト: {image_filename}")

    publish_url = f"https://graph.instagram.com/v21.0/{user_id}/media_publish"
    publish_params = {
        "creation_id": creation_id,
        "access_token": access_token,
    }
    response = requests.post(publish_url, params=publish_params)
    raise_for_status_with_body(response)
    print(f"投稿完了（画像）: {image_filename}")


def post_video_story(video_filename, user_id, access_token, repo):
    video_url = f"https://raw.githubusercontent.com/{repo}/main/{video_filename}"
    create_url = f"https://graph.instagram.com/v21.0/{user_id}/media"
    create_params = {
        "video_url": video_url,
        "media_type": "STORIES",
        "access_token": access_token,
    }
    print(f"[DEBUG] 動画コンテナ作成中: {video_url}")
    response = requests.post(create_url, params=create_params)
    raise_for_status_with_body(response)
    creation_id = response.json()["id"]
    print(f"[DEBUG] コンテナ作成完了: creation_id={creation_id}")

    # 動画の処理完了を待機
    for attempt in range(12):
        status_url = f"https://graph.instagram.com/v21.0/{creation_id}"
        status_params = {
            "fields": "status_code",
            "access_token": access_token,
        }
        status_resp = requests.get(status_url, params=status_params)
        raise_for_status_with_body(status_resp)
        status_code = status_resp.json().get("status_code")
        if status_code == "FINISHED":
            break
        elif status_code == "ERROR":
            raise RuntimeError(f"動画処理エラー: {video_filename}")
        print(f"動画処理中... ({attempt + 1}/12)")
        time.sleep(10)
    else:
        raise TimeoutError(f"動画処理タイムアウト: {video_filename}")

    publish_url = f"https://graph.instagram.com/v21.0/{user_id}/media_publish"
    publish_params = {
        "creation_id": creation_id,
        "access_token": access_token,
    }
    response = requests.post(publish_url, params=publish_params)
    raise_for_status_with_body(response)
    print(f"投稿完了（動画）: {video_filename}")


def get_today_posted_media_types(user_id, access_token):
    """本日（JST）投稿済みストーリーの media_type を投稿順に返す（["IMAGE", "VIDEO", ...]）。

    cron-job.org（07:00）と GitHub Actions schedule（08:00）の二重起動時に、
    投稿予定のメディア構成（画像N本・動画M本）と突き合わせて未済分のみ補完投稿するために使う。
    """
    JST = timezone(timedelta(hours=9))
    today_jst = datetime.now(JST).date()

    url = f"https://graph.instagram.com/v21.0/{user_id}/stories"
    params = {"fields": "timestamp,media_type", "access_token": access_token}
    response = requests.get(url, params=params)
    if not response.ok:
        # 取得失敗時は「投稿済みなし」として扱う（本日未済前提で投稿）
        print(f"[WARNING] ストーリーズ確認に失敗: {response.text}")
        return []
    stories = response.json().get("data", [])
    posted = []
    for story in stories:
        ts = story.get("timestamp")
        mt = story.get("media_type")
        if ts and mt:
            story_date = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(JST).date()
            if story_date == today_jst:
                posted.append(mt)
    if posted:
        print(f"[DEBUG] 本日投稿済みメディア: {posted}")
    return posted


if __name__ == "__main__":
    user_id = os.environ.get("INSTAGRAM_USER_ID", "")
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    missing = [name for name, val in [
        ("INSTAGRAM_USER_ID", user_id),
        ("INSTAGRAM_ACCESS_TOKEN", access_token),
        ("GITHUB_REPOSITORY", repo),
    ] if not val]
    if missing:
        print(f"[ERROR] 必須の環境変数が設定されていません: {', '.join(missing)}", file=sys.stderr)
        print("リポジトリの Settings > Secrets and variables > Actions で", file=sys.stderr)
        print("INSTAGRAM_USER_ID と INSTAGRAM_ACCESS_TOKEN を登録してください。", file=sys.stderr)
        sys.exit(1)

    print(f"[DEBUG] GITHUB_REPOSITORY={repo}")
    print(f"[DEBUG] INSTAGRAM_USER_ID={user_id}")

    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).date()
    closures = load_closures()
    announcements = load_announcements_for(today)

    # 本日の投稿予定リストを構築（順序が再実行時のスキップ判定にも使われる）
    plan = []  # [(media_type, filename), ...]
    if today in closures:
        # 臨時休診日: 動画のみ
        plan.append(("VIDEO", "closure-video.mp4"))
    else:
        # 通常日・祝日: 曜日/祝日画像
        plan.append(("IMAGE", get_today_image()))
        # 7日以内に休診日がある場合は予告動画
        for days_ahead in range(1, 8):
            upcoming = today + timedelta(days=days_ahead)
            if upcoming in closures:
                plan.append(("VIDEO", "closure-video.mp4"))
                break
        # 期間限定告知動画（複数あれば全部）
        for ann in announcements:
            plan.append(("VIDEO", ann["video"]))

    print(f"[DEBUG] 本日の投稿予定: {plan}")

    # 投稿済みメディア種別を取得（cron→Actions再実行時の二重投稿防止）
    posted = get_today_posted_media_types(user_id, access_token)
    posted_image_count = posted.count("IMAGE")
    posted_video_count = posted.count("VIDEO")

    image_skipped = 0
    video_skipped = 0
    for media_type, filename in plan:
        if media_type == "IMAGE":
            if image_skipped < posted_image_count:
                image_skipped += 1
                print(f"[SKIP] {filename}（画像は本日投稿済み）")
                continue
            print(f"本日の画像: {filename}")
            post_image_story(filename, user_id, access_token, repo)
        else:  # VIDEO
            if video_skipped < posted_video_count:
                video_skipped += 1
                print(f"[SKIP] {filename}（動画{video_skipped}本目は本日投稿済み）")
                continue
            print(f"動画投稿: {filename}")
            post_video_story(filename, user_id, access_token, repo)
