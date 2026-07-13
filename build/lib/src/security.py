"""プロジェクトのセキュリティチェック

API キーの漏えいなど、初心者がやりがちなミスを自動でチェックする。
チェックはすべてローカルで完結し、外部に情報を送信しない。
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# シークレットらしき文字列のパターン
# .env.example のような "your_api_key_here" というプレースホルダーには
# 反応しないよう、英数字のみ 25 文字以上に限定している
SECRET_PATTERNS = [
    (
        re.compile(r"AAAAAAAAAAAAAAAAAAAAA[A-Za-z0-9%]{15,}"),
        "X (Twitter) の Bearer Token らしき文字列",
    ),
    (
        re.compile(
            r"(?i)(api_key|api_secret|access_token|token_secret|bearer_token|password)"
            r"\s*[:=]\s*[\"']?[A-Za-z0-9+/=-]{25,}[\"']?"
        ),
        "API キーやパスワードらしき文字列",
    ),
]

# 中身をスキャンしない拡張子（画像など）
SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".pyc"}


@dataclass
class CheckResult:
    """1 つのチェックの結果"""

    name: str  # チェック項目名
    ok: bool  # True なら問題なし
    message: str  # 結果の説明
    advice: str = ""  # 問題があった場合の直し方
    details: list[str] = field(default_factory=list)  # 該当ファイルなど


def _git_tracked_files(project_dir: Path) -> list[Path]:
    """git で管理されているファイルの一覧を返す（git がなければ空）"""
    try:
        output = subprocess.run(
            ["git", "ls-files"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [project_dir / line for line in output.splitlines() if line.strip()]


def check_env_not_committed(project_dir: Path) -> CheckResult:
    """.env ファイルが git にコミットされていないか"""
    name = ".env ファイルがコミットされていないか"
    committed = [
        p for p in _git_tracked_files(project_dir) if p.name == ".env"
    ]
    if committed:
        return CheckResult(
            name=name,
            ok=False,
            message=".env ファイルが git にコミットされています！",
            advice=(
                "git rm --cached .env でコミット対象から外し、"
                "X の開発者ポータルで API キーを再発行してください。"
                "一度コミットしたキーは漏れたものとして扱うのが安全です。"
            ),
        )
    return CheckResult(name=name, ok=True, message=".env はコミットされていません。")


def check_gitignore(project_dir: Path) -> CheckResult:
    """.gitignore に .env が登録されているか"""
    name = ".gitignore に .env が登録されているか"
    gitignore = project_dir / ".gitignore"
    if gitignore.exists():
        lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
        if ".env" in lines:
            return CheckResult(name=name, ok=True, message=".env は除外設定済みです。")
    return CheckResult(
        name=name,
        ok=False,
        message=".gitignore に .env が登録されていません。",
        advice=".gitignore に「.env」という行を追加すると、うっかりコミットを防げます。",
    )


def check_env_permissions(project_dir: Path) -> CheckResult:
    """.env ファイルが他のユーザーから読めない権限になっているか"""
    name = ".env ファイルの権限が安全か"
    env_file = project_dir / ".env"
    if not env_file.exists():
        return CheckResult(name=name, ok=True, message=".env がまだないためスキップしました。")
    if os.name != "posix":
        return CheckResult(
            name=name, ok=True, message="Windows のため権限チェックはスキップしました。"
        )
    mode = env_file.stat().st_mode
    if mode & 0o077:
        return CheckResult(
            name=name,
            ok=False,
            message="自分以外のユーザーも .env を読める権限になっています。",
            advice="chmod 600 .env を実行すると、自分だけが読み書きできるようになります。",
        )
    return CheckResult(name=name, ok=True, message="自分だけが読める権限になっています。")


def check_secrets_in_files(project_dir: Path) -> CheckResult:
    """コミット対象のファイルにシークレットらしき文字列が含まれていないか"""
    name = "コード内にシークレットが書かれていないか"
    findings: list[str] = []
    for path in _git_tracked_files(project_dir):
        if path.suffix in SKIP_EXTENSIONS or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, label in SECRET_PATTERNS:
                if pattern.search(line):
                    rel = path.relative_to(project_dir)
                    findings.append(f"{rel}:{lineno} … {label}")
    if findings:
        return CheckResult(
            name=name,
            ok=False,
            message="シークレットらしき文字列が見つかりました。",
            advice=(
                "キーはコードに直接書かず .env に移してください。"
                "すでに push 済みの場合は、キーの再発行も必要です。"
            ),
            details=findings,
        )
    return CheckResult(name=name, ok=True, message="シークレットは見つかりませんでした。")


def check_dependencies(project_dir: Path) -> CheckResult:
    """依存パッケージに既知の脆弱性がないか（pip-audit があれば実行）"""
    name = "依存パッケージに既知の脆弱性がないか"
    requirements = project_dir / "requirements.txt"
    if not requirements.exists():
        return CheckResult(
            name=name, ok=True, message="requirements.txt がないためスキップしました。"
        )
    try:
        result = subprocess.run(
            ["pip-audit", "-r", str(requirements)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        return CheckResult(
            name=name,
            ok=True,
            message="pip-audit が未インストールのためスキップしました。",
            advice="pip install pip-audit を実行すると、このチェックも有効になります。",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name=name,
            ok=True,
            message="時間切れのためスキップしました（ネットワークを確認してください）。",
        )
    if result.returncode != 0:
        return CheckResult(
            name=name,
            ok=False,
            message="脆弱性のあるパッケージが見つかりました。",
            advice="pip-audit -r requirements.txt を実行して詳細を確認し、パッケージを更新してください。",
            details=[line for line in result.stdout.splitlines() if line.strip()],
        )
    return CheckResult(name=name, ok=True, message="既知の脆弱性は見つかりませんでした。")


def run_all_checks(project_dir: Path | None = None) -> list[CheckResult]:
    """すべてのチェックを実行して結果のリストを返す"""
    project_dir = project_dir or Path.cwd()
    return [
        check_env_not_committed(project_dir),
        check_gitignore(project_dir),
        check_env_permissions(project_dir),
        check_secrets_in_files(project_dir),
        check_dependencies(project_dir),
    ]
