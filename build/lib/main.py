#!/usr/bin/env python3
"""X (Twitter) 管理 CLI ツール"""

import argparse
import sys

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from src.client import get_client
from src.post import post_tweet
from src.followers import get_me, get_followers
from src.security import run_all_checks

console = Console()


def cmd_tweet(args: argparse.Namespace) -> None:
    text = args.text or Prompt.ask("ツイート内容を入力してください")
    if not text.strip():
        console.print("[red]内容が空です。[/red]")
        sys.exit(1)
    if len(text) > 280:
        console.print(f"[red]文字数オーバーです ({len(text)}/280)[/red]")
        sys.exit(1)

    client = get_client()
    result = post_tweet(client, text)
    tweet_id = result["id"]
    console.print(f"[green]投稿完了！[/green] https://x.com/i/web/status/{tweet_id}")


def cmd_followers(args: argparse.Namespace) -> None:
    client = get_client()

    with console.status("アカウント情報を取得中..."):
        me = get_me(client)

    console.print(f"[cyan]@{me.username}[/cyan] のフォロワーを取得中...")

    with console.status("フォロワーを取得中..."):
        followers = get_followers(client, me.id, max_results=args.limit)

    if not followers:
        console.print("[yellow]フォロワーが見つかりませんでした。[/yellow]")
        return

    table = Table(title=f"@{me.username} のフォロワー一覧 ({len(followers)} 人)")
    table.add_column("名前", style="cyan", no_wrap=True)
    table.add_column("ユーザー名", style="magenta")
    table.add_column("フォロワー数", justify="right", style="green")
    table.add_column("フォロー数", justify="right")

    for f in followers:
        metrics = f.public_metrics or {}
        table.add_row(
            f.name,
            f"@{f.username}",
            str(metrics.get("followers_count", "-")),
            str(metrics.get("following_count", "-")),
        )

    console.print(table)


def cmd_security(args: argparse.Namespace) -> None:
    console.print("[bold]セキュリティチェックを実行します...[/bold]\n")

    with console.status("チェック中..."):
        results = run_all_checks()

    table = Table(title="セキュリティチェック結果")
    table.add_column("結果", justify="center", no_wrap=True)
    table.add_column("チェック項目")
    table.add_column("説明")

    problems = [r for r in results if not r.ok]
    for r in results:
        mark = "[green]OK[/green]" if r.ok else "[red]NG[/red]"
        table.add_row(mark, r.name, r.message)

    console.print(table)

    for r in results:
        if r.ok and r.advice:
            console.print(f"[yellow]ヒント:[/yellow] {r.advice}")

    if problems:
        console.print(f"\n[red]{len(problems)} 件の問題が見つかりました。[/red]\n")
        for r in problems:
            console.print(f"[red]●[/red] [bold]{r.name}[/bold]")
            console.print(f"  [yellow]直し方:[/yellow] {r.advice}")
            for detail in r.details[:10]:
                console.print(f"  - {detail}")
        sys.exit(1)

    console.print("\n[green]問題は見つかりませんでした！このまま安心して使えます。[/green]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="X (Twitter) 管理 CLI ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="コマンド")

    # tweet
    tweet_parser = subparsers.add_parser("tweet", help="ツイートを投稿する")
    tweet_parser.add_argument("text", nargs="?", help="投稿するテキスト（省略で対話入力）")

    # followers
    followers_parser = subparsers.add_parser("followers", help="フォロワー一覧を表示する")
    followers_parser.add_argument(
        "--limit", type=int, default=200, metavar="N", help="取得するフォロワー数の上限（デフォルト: 200）"
    )

    # security
    subparsers.add_parser("security", help="セキュリティチェックを実行する")

    args = parser.parse_args()

    try:
        if args.command == "tweet":
            cmd_tweet(args)
        elif args.command == "followers":
            cmd_followers(args)
        elif args.command == "security":
            cmd_security(args)
        else:
            parser.print_help()
    except EnvironmentError as e:
        console.print(f"[red]設定エラー:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]エラー:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
