from sqlalchemy.event import listen
from CTFd.models import Users, Solves, Challenges
from .db_utils import DBUtils
from ...utils.modes import get_model
import CTFd.cache as cache

import json
import tweepy
import requests as rq


def discord_notify(solve, webhookurl):
    text = _getText(solve)

    embed = {
        "title": "First Blood!",
        "color": 15158332,
        "description": text
    }

    data = {"embeds": [embed]}

    try:
        rq.post(webhookurl, data=json.dumps(data), headers={"Content-Type": "application/json"})
    except rq.exceptions.RequestException as e:
        print(e)


def other_notify(solve, webhookurl):
    text = _getText(solve)
    data = {"message": text}
    try:
        rq.get(webhookurl, params=data)
    except rq.exceptions.RequestException as e:
        print(e)


def twitter_notify(solve, consumer_key, consumer_secret, access_token, access_token_secret, hashtags):
    text = _getText(solve, hashtags)
    try:
        AUTH = tweepy.OAuthHandler(consumer_key, consumer_secret)
        AUTH.set_access_token(access_token, access_token_secret)
        API = tweepy.API(AUTH)
        API.update_status(status=text)
    except tweepy.TweepError as e:
        print(e)


def on_solve(mapper, conn, solve):
    config = DBUtils.get_config()
    solves = _getSolves(solve.challenge_id)

    if solves == 1:
        if config.get("discord_notifier") == "true":
            discord_notify(solve, config.get("discord_webhook_url"))

        if config.get("twitter_notifier") == "true":
            twitter_notify(solve, config.get("twitter_consumer_key"), config.get("twitter_consumer_secret"),
                           config.get("twitter_access_token"), config.get("twitter_access_token_secret"),
                           config.get("twitter_hashtags"))
        
        if config.get("other_notifier") == "true":
            other_notify(solve, config.get("other_webhook_url"))


def _getSolves(challenge_id):
    Model = get_model()

    solve_count = (
        Solves.query.join(Model, Solves.account_id == Model.id)
            .filter(
            Solves.challenge_id == challenge_id,
            Model.hidden == False,
            Model.banned == False,
        )
            .count()
    )

    return solve_count


def _getChallenge(challenge_id):
    challenge = Challenges.query.filter_by(id=challenge_id).first()
    return challenge


def _getUser(user_id):
    user = Users.query.filter_by(id=user_id).first()
    return user


def _getText(solve, hashtags=""):
    cache.clear_standings()
    user = _getUser(solve.user_id)
    challenge = _getChallenge(solve.challenge_id)

    score = user.get_score(admin=True)
    place = user.get_place(admin=True)

    if not hashtags == "":
        text = f"{user.name} 在 {challenge.name} 获得一血，并且现在在第 {place} 名，并获得了 {score} 分 {hashtags}"
    else:
        text = f"{user.name} 在 {challenge.name} 获得一血，并且现在在第 {place} 名，并获得了 {score} 分"

    return text


def load_hooks():
    listen(Solves, "after_insert", on_solve)
