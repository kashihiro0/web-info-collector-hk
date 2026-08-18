# Web情報収集アプリ

食品輸出・海外進出・海外輸出コンテナー・海上輸送・海外外食開店・日本食に関する
ニュースを Google News RSS（日本語＋英語）から3時間おきに集めて、
Gmail からメールで送信する GitHub Actions ベースのツール。

## 動くしくみ

1. `.github/workflows/collect.yml` が3時間ごと（`0 */3 * * *`）に GitHub Actions 上で `collect.py` を実行
2. `collect.py` が `config.yaml` の各カテゴリーについて、日本語・英語それぞれで
   Google News RSS（`news.google.com/rss/search`、認証不要）を検索
3. カテゴリー別にまとめたテキストメールを Gmail 経由で送信

> Google News RSS の利用規約は「個人利用目的のフィードリーダーでの表示」を
> 前提としている（フィード内に明記）。業務での継続利用を想定する場合は、
> 将来的に NewsAPI や商用ニュースAPIへの切り替えも検討してください。

## セットアップ手順

### 1. Gmail アプリパスワードの取得

1. 送信に使う Gmail アカウントで2段階認証を有効化
2. [Googleアカウントのセキュリティ設定](https://myaccount.google.com/security) →
   「アプリパスワード」で16桁のパスワードを発行

### 2. GitHub リポジトリの準備

このディレクトリを GitHub リポジトリにする（まだの場合）:

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create <repo名> --private --source=. --push
```

### 3. GitHub Secrets の登録

リポジトリの Settings → Secrets and variables → Actions で以下を登録:

| Secret名 | 内容 |
|---|---|
| `GMAIL_ADDRESS` | 送信元Gmailアドレス |
| `GMAIL_APP_PASSWORD` | 手順1で発行したアプリパスワード |
| `MAIL_TO` | 送信先アドレス（省略時は `GMAIL_ADDRESS` 宛） |

### 4. 動作確認

Secrets登録後、Actions タブから `Collect industry news and email` を選び
「Run workflow」で手動実行して、メールが届くか確認する。

## ローカルでのテスト実行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export GMAIL_ADDRESS=xxx@gmail.com
export GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
export MAIL_TO=xxx@gmail.com

python collect.py
```

## 設定変更

`config.yaml` で以下を調整できる:

- `categories`: カテゴリー名と検索クエリ（日本語 `query_ja` / 英語 `query_en`）
  - カテゴリーの追加・削除・キーワード変更が可能
- `items_per_query`: 各カテゴリー・各言語ごとに取得する件数（デフォルト3件）

現在のカテゴリー：食品 / 海外進出 / 海外輸出コンテナー / 輸出海上輸出 / 海外へ外食開店 / 日本食

実行頻度を変えたい場合は `.github/workflows/collect.yml` の `cron` を編集する
（例: 毎時なら `0 * * * *`）。
