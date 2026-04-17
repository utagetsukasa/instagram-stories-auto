import os
import json
import sys
import time
import requests
import jpholiday
from datetime import date, datetime, timedelta, timezone

CLOSURES_FILE = "closures.json"


def load_closures():
    if not os.path.exists(CLOSURES_FILE):
        return []
    with open(CLOSURES_FILE, "r") as f:
        data = json.load(f)
    return [date.fromisoformat(d) for d in data.get("closures", [])]


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


def already_posted_today(user_id, access_token):
    """今日（JST）すでにストーリーズを投稿済みか確認する。"""
    JST = timezone(timedelta(hours=9))
    today_jst = datetime.now(JST).date()

    url = f"https://graph.instagram.com/v21.0/{user_id}/stories"
    params = {"fields": "timestamp", "access_token": access_token}
    response = requests.get(url, params=params)
    if not response.ok:
        # ストーリーズ取得に失敗した場合は投稿未済として扱う
        print(f"[WARNING] ストーリーズ確認に失敗: {response.text}")
        return False
    stories = response.json().get("data", [])
    for story in stories:
        ts = story.get("timestamp")
        if ts:
            story_date = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(JST).date()
            if story_date == today_jst:
                print(f"[DEBUG] 本日投稿済みのストーリーを検出: {ts}")
                return True
    return False


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

    # 本日すでに投稿済みの場合はスキップ（二重投稿防止）
    if already_posted_today(user_id, access_token):
        print("本日はすでに投稿済みです。スキップします。")
        sys.exit(0)

    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).date()
    closures = load_closures()

    if today in closures:
        # 臨時休診日: 動画のみ投稿
        print("本日は臨時休診日です。動画のみ投稿します。")
        post_video_story("closure-video.mp4", user_id, access_token, repo)
    else:
        # 通常日または祝日: 曜日・祝日画像を投稿
        image = get_today_image()
        print(f"本日の画像: {image}")
        post_image_story(image, user_id, access_token, repo)

        # 7日以内に休診日がある場合は予告動画も投稿
        for days_ahead in range(1, 8):
            upcoming = today + timedelta(days=days_ahead)
            if upcoming in closures:
                print(f"臨時休診日（{upcoming}）まで{days_ahead}日：予告動画を投稿します。")
                post_video_story("closure-video.mp4", user_id, access_token, repo)
                break
