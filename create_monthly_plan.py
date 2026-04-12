import os
import json
import requests
import jpholiday
import calendar
from datetime import date, timedelta

CLOSURES_FILE = "closures.json"

WEEKDAY_LABELS = {
    0: "monday.png",
    1: "tuesday.png",
    2: "wednesday.png",
    3: "thursday.png",
    4: "friday.png",
    5: "saturday.png",
    6: "sunday.png",
}

WEEKDAY_JP = {
    0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"
}


def load_closures():
    if not os.path.exists(CLOSURES_FILE):
        return []
    with open(CLOSURES_FILE, "r") as f:
        data = json.load(f)
    return [date.fromisoformat(d) for d in data.get("closures", [])]


def get_post_plan(target_date, closures):
    if target_date in closures:
        return ["closure-video.mp4（臨時休診日）"]

    posts = []
    holiday_name = jpholiday.is_holiday_name(target_date)
    if holiday_name:
        posts.append(f"holiday.png（{holiday_name}）")
    else:
        posts.append(WEEKDAY_LABELS[target_date.weekday()])

    # 7日以内に休診日がある場合
    for d in range(1, 8):
        future = target_date + timedelta(days=d)
        if future in closures:
            posts.append(f"closure-video.mp4（休診{d}日前予告）")
            break

    return posts


def build_issue_body(year, month, closures):
    num_days = calendar.monthrange(year, month)[1]
    lines = [
        f"## {year}年{month}月 Instagram Stories 投稿プラン",
        "",
        "| 日付 | 曜日 | 投稿内容 |",
        "|------|------|----------|",
    ]

    for day in range(1, num_days + 1):
        d = date(year, month, day)
        weekday = WEEKDAY_JP[d.weekday()]
        posts = get_post_plan(d, closures)
        content = " + ".join(posts)
        lines.append(f"| {month}/{day} | {weekday} | {content} |")

    lines += [
        "",
        "---",
        f"> 臨時休診日は `closures.json` で管理されています。",
        f"> 変更が必要な場合は `closures.json` を更新してください。",
    ]
    return "\n".join(lines)


def create_github_issue(title, body):
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"title": title, "body": body}
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    issue_url = response.json()["html_url"]
    print(f"Issue作成完了: {issue_url}")


if __name__ == "__main__":
    today = date.today()
    # 翌月を対象にする
    if today.month == 12:
        target_year, target_month = today.year + 1, 1
    else:
        target_year, target_month = today.year, today.month + 1

    closures = load_closures()
    title = f"{target_year}年{target_month}月 投稿プラン"
    body = build_issue_body(target_year, target_month, closures)
    create_github_issue(title, body)
