"""指定カテゴリーの業界ニュースを Google News RSS から集めてメール送信する。

GitHub Actions から3時間おきに実行される想定。
必要な環境変数:
  GMAIL_ADDRESS         - 送信元 Gmail アドレス
  GMAIL_APP_PASSWORD    - Gmail のアプリパスワード（2段階認証が必要）
  MAIL_TO               - 送信先アドレス（省略時は GMAIL_ADDRESS 宛）
"""

import os
import smtplib
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

import requests
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
NEWS_USER_AGENT = "Mozilla/5.0 (compatible; web-info-collector/1.0)"
MAX_AGE_DAYS = 30


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_google_news(query, hl, gl, limit):
    url = "https://news.google.com/rss/search"
    params = {
        "q": f"{query} when:{MAX_AGE_DAYS}d",
        "hl": hl,
        "gl": gl,
        "ceid": f"{gl}:{hl}",
    }
    resp = requests.get(
        url, params=params, headers={"User-Agent": NEWS_USER_AGENT}, timeout=15
    )
    resp.raise_for_status()

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    root = ET.fromstring(resp.content)
    items = []
    for item in root.findall("./channel/item"):
        pub_date_text = item.findtext("pubDate", default="")
        try:
            pub_date = parsedate_to_datetime(pub_date_text)
        except (TypeError, ValueError):
            pub_date = None
        if pub_date is not None and pub_date < cutoff:
            continue

        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        source = item.findtext("source", default="").strip()
        items.append({"title": title, "link": link, "source": source})
        if len(items) >= limit:
            break
    return items


def build_site_restricted_query(query, domains):
    site_filter = " OR ".join(f"site:{domain}" for domain in domains)
    return f"{query} ({site_filter})"


def fetch_category_news(category, items_per_query, named_sources, items_per_named_query):
    named_items = []
    if named_sources:
        domains = [s["domain"] for s in named_sources]
        named_query = build_site_restricted_query(category["query_ja"], domains)
        named_items = fetch_google_news(named_query, "ja", "JP", items_per_named_query)

    ja_items = fetch_google_news(category["query_ja"], "ja", "JP", items_per_query)
    en_items = fetch_google_news(category["query_en"], "en-US", "US", items_per_query)

    named_links = {item["link"] for item in named_items}
    ja_items = [item for item in ja_items if item["link"] not in named_links]

    return {"name": category["name"], "ja": ja_items, "en": en_items, "named": named_items}


def build_email_body(category_results, subject_prefix):
    lines = [f"{subject_prefix}\n"]

    for cat in category_results:
        lines.append(f"■ {cat['name']}\n")

        if cat["named"]:
            lines.append("[主要紙・専門紙]")
            for i, item in enumerate(cat["named"], 1):
                source = f" ({item['source']})" if item["source"] else ""
                lines.append(f"{i}. {item['title']}{source}")
                lines.append(f"   {item['link']}")

        if cat["ja"]:
            lines.append("[日本語]")
            for i, item in enumerate(cat["ja"], 1):
                source = f" ({item['source']})" if item["source"] else ""
                lines.append(f"{i}. {item['title']}{source}")
                lines.append(f"   {item['link']}")

        if cat["en"]:
            lines.append("[English]")
            for i, item in enumerate(cat["en"], 1):
                source = f" ({item['source']})" if item["source"] else ""
                lines.append(f"{i}. {item['title']}{source}")
                lines.append(f"   {item['link']}")

        lines.append("")

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

    gmail_address = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    gmail_app_password = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()
    mail_to = (os.environ.get("MAIL_TO") or "").strip() or gmail_address

    missing = [
        name
        for name, val in [
            ("GMAIL_ADDRESS", gmail_address),
            ("GMAIL_APP_PASSWORD", gmail_app_password),
        ]
        if not val
    ]
    if missing:
        print(f"環境変数が不足しています: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    items_per_query = config["items_per_query"]
    named_sources = config.get("named_sources", [])
    items_per_named_query = config.get("items_per_named_query", items_per_query)
    category_results = [
        fetch_category_news(category, items_per_query, named_sources, items_per_named_query)
        for category in config["categories"]
    ]

    subject_prefix = config["mail"]["subject_prefix"]
    body = build_email_body(category_results, subject_prefix)

    send_email(subject_prefix, body, gmail_address, gmail_app_password, mail_to)
    print("メール送信完了")


if __name__ == "__main__":
    main()
