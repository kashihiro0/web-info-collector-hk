# Web情報収集アプリ

Hacker News の人気投稿と YouTube 急上昇（日本）の TOP10 を3時間おきに集めて、
Gmail からメールで送信する GitHub Actions ベースのツール。

> Reddit は2025年11月からの「Responsible Builder Policy」により、新規の
> API利用登録が手動審査制になり個人開発では実質利用できなくなったため、
> 認証不要で無料の Hacker News API に差し替えている。

## 動くしくみ

1. `.github/workflows/collect.yml` が3時間ごと（`0 */3 * * *`）に GitHub Actions 上で `collect.py` を実行
2. `collect.py` が Hacker News API（認証不要）と YouTube Data API v3 からデータ取得
3. TOP10をまとめたテキストメールを Gmail 経由で送信

## セットアップ手順

### 1. YouTube Data API キーの取得

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 「YouTube Data API v3」を有効化
3. 「認証情報」から API キーを発行

無料枠は1日10,000ユニットで、この用途（3時間ごと・1日8回実行）なら十分収まります。

### 2. Gmail アプリパスワードの取得

1. 送信に使う Gmail アカウントで2段階認証を有効化
2. [Googleアカウントのセキュリティ設定](https://myaccount.google.com/security) →
   「アプリパスワード」で16桁のパスワードを発行

### 3. GitHub リポジトリの準備

このディレクトリを GitHub リポジトリにする（まだの場合）:

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create <repo名> --private --source=. --push
```

### 4. GitHub Secrets の登録

リポジトリの Settings → Secrets and variables → Actions で以下を登録:

| Secret名 | 内容 |
|---|---|
| `YOUTUBE_API_KEY` | 手順1で発行したAPIキー |
| `GMAIL_ADDRESS` | 送信元Gmailアドレス |
| `GMAIL_APP_PASSWORD` | 手順2で発行したアプリパスワード |
| `MAIL_TO` | 送信先アドレス（省略時は `GMAIL_ADDRESS` 宛） |

### 5. 動作確認

Secrets登録後、Actions タブから `Collect and email top10` を選び
「Run workflow」で手動実行して、メールが届くか確認する。

## ローカルでのテスト実行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export YOUTUBE_API_KEY=xxx
export GMAIL_ADDRESS=xxx@gmail.com
export GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
export MAIL_TO=xxx@gmail.com

python collect.py
```

## 設定変更

`config.yaml` で以下を調整できる:

- `hacker_news.top_n`: Hacker News の取得件数
- `youtube.region_code`: 急上昇の対象地域（デフォルト `JP`）
- 各 `top_n`: 取得件数

実行頻度を変えたい場合は `.github/workflows/collect.yml` の `cron` を編集する
（例: 毎時なら `0 * * * *`）。
