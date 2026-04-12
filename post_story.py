import os
import json
import time
import requests
import jpholiday
from datetime import date, timedelta

CLOSURES_FILE = "closures.json"


def load_closures():
    if not os.path.exists(CLOSURES_FILE):
        return []
    with open(CLOSURES_FILE, "r") as f:
        data = json.load(f)
    return [date.fromisoformat(d) for d in data.get("closures", [])]


def get_today_image():
    today = date.today()
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


def post_image_story(image_filename, user_id, access_token, repo):
    image_url = f"https://raw.githubusercontent.com/{repo}/main/{image_filename}"
    create_url = f"https://graph.instagram.com/v21.0/{user_id}/media"
    create_params = {
        "image_url": image_url,
        "media_type": "STORIES",
        "access_token": access_token,
    }
    response = requests.post(create_url, params=create_params)
    response.raise_for_status()
    creation_id = response.json()["id"]

    publish_url = f"https://graph.instagram.com/v21.0/{user_id}/media_publish"
    publish_params = {
        "creation_id": creation_id,
        "access_token": access_token,
    }
    response = requests.post(publish_url, params=publish_params)
    response.raise_for_status()
    print(f"投稿完了（画像）: {image_filename}")


def post_video_story(video_filename, user_id, access_token, repo):
    video_url = f"https://raw.githubusercontent.com/{repo}/main/{video_filename}"
    create_url = f"https://graph.instagram.com/v21.0/{user_id}/media"
    create_params = {
        "video_url": video_url,
        "media_type": "STORIES",
        "access_token": access_token,
    }
    response = requests.post(create_url, params=create_params)
    response.raise_for_status()
    creation_id = response.json()["id"]

    # 動画の処理完了を待機
    for attempt in range(12):
        status_url = f"https://graph.instagram.com/v21.0/{creation_id}"
        status_params = {
            "fields": "status_code",
            "access_token": access_token,
        }
        status_resp = requests.get(status_url, params=status_params)
        status_resp.raise_for_status()
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
    response.raise_for_status()
    print(f"投稿完了（動画）: {video_filename}")


if __name__ == "__main__":
    user_id = os.environ["INSTAGRAM_USER_ID"]
    access_token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]

    today = date.today()
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
