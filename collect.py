"""Reddit と YouTube 急上昇の TOP10 を集めてメール送信する。

GitHub Actions から3時間おきに実行される想定。
必要な環境変数:
  YOUTUBE_API_KEY       - Google Cloud Console で発行した YouTube Data API v3 のキー
  GMAIL_ADDRESS         - 送信元 Gmail アドレス
  GMAIL_APP_PASSWORD    - Gmail のアプリパスワード（2段階認証が必要）
  MAIL_TO               - 送信先アドレス（省略時は GMAIL_ADDRESS 宛）
任意:
  REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET - 未設定なら Reddit 収集はスキップ
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


REDDIT_USER_AGENT = "web-info-collector/1.0 (personal script)"


def get_reddit_access_token(client_id, client_secret):
    resp = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": REDDIT_USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_reddit_top(subreddits, time_filter, top_n, client_id, client_secret):
    token = get_reddit_access_token(client_id, client_secret)
    headers = {
        "User-Agent": REDDIT_USER_AGENT,
        "Authorization": f"bearer {token}",
    }
    items = []
    for sub in subreddits:
        url = f"https://oauth.reddit.com/r/{sub}/top"
        params = {"t": time_filter, "limit": top_n}
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        for child in resp.json()["data"]["children"]:
            d = child["data"]
            items.append(
                {
                    "title": d["title"],
                    "score": d["score"],
                    "url": f"https://reddit.com{d['permalink']}",
                    "subreddit": d["subreddit"],
                }
            )
    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:top_n]


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


def build_email_body(reddit_items, youtube_items, subject_prefix):
    lines = [f"{subject_prefix}\n"]

    lines.append("■ Reddit 人気投稿\n")
    if reddit_items:
        for i, item in enumerate(reddit_items, 1):
            lines.append(f"{i}. [{item['subreddit']}] {item['title']} (score: {item['score']})")
            lines.append(f"   {item['url']}")
    else:
        lines.append("（未設定のためスキップ）")

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

    reddit_client_id = os.environ.get("REDDIT_CLIENT_ID")
    reddit_client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
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

    reddit_items = []
    if reddit_client_id and reddit_client_secret:
        reddit_items = fetch_reddit_top(
            config["reddit"]["subreddits"],
            config["reddit"]["time_filter"],
            config["reddit"]["top_n"],
            reddit_client_id,
            reddit_client_secret,
        )
    else:
        print("Reddit の認証情報がないため、Reddit 収集はスキップします")
    youtube_items = fetch_youtube_trending(
        youtube_api_key,
        config["youtube"]["region_code"],
        config["youtube"]["top_n"],
    )

    subject_prefix = config["mail"]["subject_prefix"]
    body = build_email_body(reddit_items, youtube_items, subject_prefix)
    subject = subject_prefix

    send_email(subject, body, gmail_address, gmail_app_password, mail_to)
    print("メール送信完了")


if __name__ == "__main__":
    main()
