# kirakira-sns

X (Twitter) 管理 CLI ツールです。ツイート投稿・フォロワー一覧に加えて、
**初心者でも使えるセキュリティチェック機能**が付いています。

## インストール

```bash
pip install ".[security]"
```

インストールすると `kirakira` コマンドが使えるようになります。
（インストールせずに `python main.py ...` で実行することもできます）

## 使い方

### セキュリティチェック

```bash
kirakira security
```

以下を自動でチェックして、問題があれば**直し方も日本語で表示**します。

- `.env`（API キーの保存ファイル）を git にコミットしてしまっていないか
- `.gitignore` に `.env` が登録されているか
- `.env` が自分以外のユーザーからも読める権限になっていないか
- コードの中に API キーやパスワードを直接書いてしまっていないか
- 使っているパッケージに既知の脆弱性がないか

外部にデータを送ることはなく、すべて自分のパソコンの中だけでチェックします。

### ツイートを投稿する

```bash
kirakira tweet "こんにちは！"
```

### フォロワー一覧を表示する

```bash
kirakira followers --limit 100
```

## API キーの設定

`.env.example` をコピーして `.env` を作り、
[X の開発者ポータル](https://developer.twitter.com/en/portal/dashboard)で取得したキーを記入してください。

```bash
cp .env.example .env
```

セキュリティの詳細は [SECURITY.md](SECURITY.md) を見てください。
