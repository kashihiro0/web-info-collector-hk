"""Hacker News と YouTube 急上昇の TOP10 を集めてメール送信する。

GitHub Actions から3時間おきに実行される想定。
必要な環境変数:
  YOUTUBE_API_KEY       - Google Cloud Console で発行した YouTube Data API v3 のキー
  GMAIL_ADDRESS         - 送信元 Gmail アドレス
  GMAIL_APP_PASSWORD    - Gmail のアプリパスワード（2段階認証が必要）
  MAIL_TO               - 送信先アドレス（省略時は GMAIL_ADDRESS 宛）
"""

import os
import smtplib
import sys
from email.mime.text import MIMEText

import requests
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


HN_BASE_URL = "https://hacker-news.firebaseio.com/v0"


def fetch_hn_top(top_n):
    resp = requests.get(f"{HN_BASE_URL}/topstories.json", timeout=15)
    resp.raise_for_status()
    story_ids = resp.json()[:top_n]

    items = []
    for story_id in story_ids:
        resp = requests.get(f"{HN_BASE_URL}/item/{story_id}.json", timeout=15)
        resp.raise_for_status()
        d = resp.json()
        items.append(
            {
                "title": d.get("title", "(no title)"),
                "score": d.get("score", 0),
                "url": d.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
            }
        )
    return items


def fetch_youtube_trending(api_key, region_code, top_n):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": top_n,
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    items = []
    for v in resp.json().get("items", []):
        items.append(
            {
                "title": v["snippet"]["title"],
                "channel": v["snippet"]["channelTitle"],
                "views": int(v["statistics"].get("viewCount", 0)),
                "url": f"https://www.youtube.com/watch?v={v['id']}",
            }
        )
    return items[:top_n]


def build_email_body(hn_items, youtube_items, subject_prefix):
    lines = [f"{subject_prefix}\n"]

    lines.append("■ Hacker News 人気投稿\n")
    for i, item in enumerate(hn_items, 1):
        lines.append(f"{i}. {item['title']} (score: {item['score']})")
        lines.append(f"   {item['url']}")

    lines.append("\n■ YouTube 急上昇\n")
    for i, item in enumerate(youtube_items, 1):
        lines.append(f"{i}. {item['title']} - {item['channel']} ({item['views']:,} views)")
        lines.append(f"   {item['url']}")

    return "\n".join(lines)


def send_email(subject, body, gmail_address, gmail_app_password, mail_to):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = mail_to

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [mail_to], msg.as_string())


def main():
    config = load_config()

    youtube_api_key = os.environ.get("YOUTUBE_API_KEY")
    gmail_address = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    gmail_app_password = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()
    mail_to = (os.environ.get("MAIL_TO") or "").strip() or gmail_address

    missing = [
        name
        for name, val in [
            ("YOUTUBE_API_KEY", youtube_api_key),
            ("GMAIL_ADDRESS", gmail_address),
            ("GMAIL_APP_PASSWORD", gmail_app_password),
        ]
        if not val
    ]
    if missing:
        print(f"環境変数が不足しています: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    hn_items = fetch_hn_top(config["hacker_news"]["top_n"])
    youtube_items = fetch_youtube_trending(
        youtube_api_key,
        config["youtube"]["region_code"],
        config["youtube"]["top_n"],
    )

    subject_prefix = config["mail"]["subject_prefix"]
    body = build_email_body(hn_items, youtube_items, subject_prefix)
    subject = subject_prefix

    send_email(subject, body, gmail_address, gmail_app_password, mail_to)
    print("メール送信完了")


if __name__ == "__main__":
    main()
