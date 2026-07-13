# セキュリティ

## セキュリティチェックコマンド（初心者向け）

インストール後、次の 1 コマンドで手元のセキュリティチェックができます。

```bash
kirakira security
```

API キーの漏えいやファイル権限などを自動でチェックし、問題があれば直し方を日本語で表示します。
詳しくは [README.md](README.md) を見てください。

## CI での自動チェック

このリポジトリでは、外部のセキュリティツールを使って自動チェックも行っています。

## 導入しているツール

| ツール | 目的 | 実行タイミング |
| --- | --- | --- |
| [pip-audit](https://github.com/pypa/pip-audit) | 依存パッケージ（tweepy など）に既知の脆弱性がないかチェック | push / PR / 毎週月曜 |
| [Bandit](https://github.com/PyCQA/bandit) | Python コードの静的セキュリティ解析（危険な関数の使用などを検出） | push / PR / 毎週月曜 |
| [Gitleaks](https://github.com/gitleaks/gitleaks) | API キーやトークンなどのシークレットがコミットに含まれていないか検出 | push / PR / 毎週月曜 |
| [Dependabot](https://docs.github.com/ja/code-security/dependabot) | 依存パッケージ・GitHub Actions の更新 PR を自動作成 | 毎週月曜 |

CI の設定は `.github/workflows/security.yml`、Dependabot の設定は `.github/dependabot.yml` にあります。

## ローカルでの実行方法

```bash
pip install pip-audit bandit

# 依存パッケージの脆弱性チェック
pip-audit -r requirements.txt

# コードの静的セキュリティ解析
bandit -r src main.py
```

## 認証情報の取り扱い

- X API のキー・トークンは `.env` ファイルに保存し、**絶対にコミットしないでください**（`.gitignore` で除外済み）。
- 万が一シークレットをコミットしてしまった場合は、X の開発者ポータルで**キーを再発行（ローテーション）**してください。履歴からの削除だけでは不十分です。
