import tweepy


def post_tweet(client: tweepy.Client, text: str) -> dict:
    response = client.create_tweet(text=text)
    return response.data
