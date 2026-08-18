# Web情報収集アプリ

Reddit（r/all の人気投稿）と YouTube 急上昇（日本）の TOP10 を3時間おきに集めて、
Gmail からメールで送信する GitHub Actions ベースのツール。

## 動くしくみ

1. `.github/workflows/collect.yml` が3時間ごと（`0 */3 * * *`）に GitHub Actions 上で `collect.py` を実行
2. `collect.py` が Reddit API（OAuth）と YouTube Data API v3 からデータ取得
3. TOP10をまとめたテキストメールを Gmail 経由で送信

## セットアップ手順

### 1. Reddit アプリの作成（無料）

Redditの公開JSONエンドポイントは匿名アクセスをブロックするようになったため、
無料のOAuthアプリ登録が必要。

1. [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) にログインして開く
2. 「create another app...」→ タイプは `script` を選択
3. name は任意（例: `web-info-collector`）、redirect uri は `http://localhost` でよい
4. 作成後、アプリ名の下に出る文字列が `client_id`、「secret」欄が `client_secret`

無料枠は1分あたり約100リクエストまでで、この用途には十分。

### 2. YouTube Data API キーの取得

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 「YouTube Data API v3」を有効化
3. 「認証情報」から API キーを発行

無料枠は1日10,000ユニットで、この用途（3時間ごと・1日8回実行）なら十分収まります。

### 3. Gmail アプリパスワードの取得

1. 送信に使う Gmail アカウントで2段階認証を有効化
2. [Googleアカウントのセキュリティ設定](https://myaccount.google.com/security) →
   「アプリパスワード」で16桁のパスワードを発行

### 4. GitHub リポジトリの準備

このディレクトリを GitHub リポジトリにする（まだの場合）:

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create <repo名> --private --source=. --push
```

### 5. GitHub Secrets の登録

リポジトリの Settings → Secrets and variables → Actions で以下を登録:

| Secret名 | 内容 |
|---|---|
| `REDDIT_CLIENT_ID` | 手順1で発行したclient_id |
| `REDDIT_CLIENT_SECRET` | 手順1で発行したclient_secret |
| `YOUTUBE_API_KEY` | 手順2で発行したAPIキー |
| `GMAIL_ADDRESS` | 送信元Gmailアドレス |
| `GMAIL_APP_PASSWORD` | 手順3で発行したアプリパスワード |
| `MAIL_TO` | 送信先アドレス（省略時は `GMAIL_ADDRESS` 宛） |

### 6. 動作確認

Secrets登録後、Actions タブから `Collect and email top10` を選び
「Run workflow」で手動実行して、メールが届くか確認する。

## ローカルでのテスト実行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export REDDIT_CLIENT_ID=xxx
export REDDIT_CLIENT_SECRET=xxx
export YOUTUBE_API_KEY=xxx
export GMAIL_ADDRESS=xxx@gmail.com
export GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
export MAIL_TO=xxx@gmail.com

python collect.py
```

## 設定変更

`config.yaml` で以下を調整できる:

- `reddit.subreddits`: 対象サブレディット（複数可、デフォルトは `all`）
- `reddit.time_filter`: `hour` / `day` / `week` など
- `youtube.region_code`: 急上昇の対象地域（デフォルト `JP`）
- 各 `top_n`: 取得件数

実行頻度を変えたい場合は `.github/workflows/collect.yml` の `cron` を編集する
（例: 毎時なら `0 * * * *`）。
