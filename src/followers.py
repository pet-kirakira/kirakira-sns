import tweepy


def get_me(client: tweepy.Client) -> tweepy.User:
    response = client.get_me(user_fields=["name", "username", "public_metrics"])
    if not response.data:
        raise RuntimeError("自分のアカウント情報を取得できませんでした。")
    return response.data


def get_followers(client: tweepy.Client, user_id: int, max_results: int = 1000) -> list[tweepy.User]:
    followers = []
    paginator = tweepy.Paginator(
        client.get_users_followers,
        id=user_id,
        max_results=min(max_results, 1000),
        user_fields=["name", "username", "public_metrics"],
    )
    for page in paginator:
        if page.data:
            followers.extend(page.data)
        if len(followers) >= max_results:
            break
    return followers[:max_results]
