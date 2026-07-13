import os
import tweepy
from dotenv import load_dotenv

load_dotenv()


def get_client() -> tweepy.Client:
    required = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(
            f"以下の環境変数が未設定です: {', '.join(missing)}\n"
            ".env.example を参考に .env ファイルを作成してください。"
        )

    return tweepy.Client(
        bearer_token=os.getenv("BEARER_TOKEN"),
        consumer_key=os.getenv("API_KEY"),
        consumer_secret=os.getenv("API_SECRET"),
        access_token=os.getenv("ACCESS_TOKEN"),
        access_token_secret=os.getenv("ACCESS_TOKEN_SECRET"),
        wait_on_rate_limit=True,
    )
