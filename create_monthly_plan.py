import os
import requests
import jpholiday
import calendar
from datetime import date

# 投稿予定の組み立ては post_story.py を唯一の正とする（二重実装を避けるため）
from post_story import build_plan, load_announcements_for, load_no_post_dates

WEEKDAY_JP = {
    0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"
}


def get_post_plan(target_date, no_post_dates):
    """その日に投稿されるファイル名を、表示用のラベルにして返す。"""
    if target_date in no_post_dates:
        return ["（休業日・投稿なし）"]

    plan = build_plan(target_date, load_announcements_for(target_date))
    labels = []
    for _, filename in plan:
        if filename == "holiday.png":
            holiday_name = jpholiday.is_holiday_name(target_date)
            labels.append(f"holiday.png（{holiday_name}）" if holiday_name else filename)
        else:
            labels.append(filename)
    return labels


def build_issue_body(year, month, no_post_dates):
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
        posts = get_post_plan(d, no_post_dates)
        content = " + ".join(posts)
        lines.append(f"| {month}/{day} | {weekday} | {content} |")

    lines += [
        "",
        "---",
        "> 特定日の差し替え・追加投稿は `announcements.json` で管理されています。",
        "> 投稿そのものを休む日は `no_post_dates.json` です。",
        "> 設定方法は README を参照してください。",
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

    no_post_dates = load_no_post_dates()
    title = f"{target_year}年{target_month}月 投稿プラン"
    body = build_issue_body(target_year, target_month, no_post_dates)
    create_github_issue(title, body)
