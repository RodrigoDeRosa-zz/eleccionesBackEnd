import pytz
import datetime
from twython import Twython, TwythonRateLimitError, TwythonError

from src.db.dao.RawFollowerDAO import RawFollowerDAO
from src.exception import CredentialsAlreadyInUseError
from src.model.followers.RawFollower import RawFollower

from src.model.tweets.RawTweet import RawTweet

from src.service.credentials.CredentialService import CredentialService
from src.service.tweets.FollowersQueueService import FollowersQueueService
from src.util.concurrency.AsyncThreadPoolExecutor import AsyncThreadPoolExecutor

from src.util.logging.Logger import Logger

MAX_TWEETS = 200
PRIVATE_USER_ERROR_CODE = 401


class TweetUpdateService:

    @classmethod
    def update_tweets(cls):
        """ Update tweet of some candidates' followers. """
        cls.get_logger().info('Starting follower updating process.')
        try:
            credentials = CredentialService().get_all_credentials_for_service(cls.__name__)
        except CredentialsAlreadyInUseError as caiue:
            cls.get_logger().error(caiue.message)
            cls.get_logger().warning('Tweets updating process skipped.')
            return
        # Run tweet update process
        AsyncThreadPoolExecutor().run(cls.download_tweets_with_credential, credentials)
        cls.get_logger().info('Stoped tweet updating')

    @classmethod
    def download_tweets_with_credential(cls, credential):
        """ Update followers' tweets with an specific Twitter Api Credential. """
        cls.get_logger().info(f'Starting follower updating with credential {credential.id}.')
        # Create Twython instance for credential
        twitter = cls.twitter(credential)
        # While there are followers to update
        while followers:
            followers = cls.get_followers_to_update()
            for follower, last_update in followers.items():
                follower_download_tweets = []
                min_tweet_date = datetime.datetime.strptime(last_update, '%a %b %d %H:%M:%S %z %Y') \
                    .astimezone(pytz.timezone('America/Argentina/Buenos_Aires'))
                continue_downloading = cls.download_tweets_and_validate(twitter, follower, follower_download_tweets,
                                                                        min_tweet_date, True)
                while continue_downloading:
                    max_id = follower_download_tweets[len(follower_download_tweets) - 1]['id'] - 1
                    continue_downloading = cls.download_tweets_and_validate(twitter, follower, follower_download_tweets,
                                                                            min_tweet_date, False, max_id)
                cls.store_new_tweets(follower, follower_download_tweets, min_tweet_date)
                if len(follower_download_tweets) != 0:
                    cls.update_follower(follower)
        cls.get_logger().warning(f'Stoping follower updating proccess with {credential}.')
        CredentialService().unlock_credential(credential, cls.__name__)

    @classmethod
    def get_followers_to_update(cls):
        """ Get the followers to be updated from FollowersQueueService. """
        return FollowersQueueService().get_followers_to_update()

    @classmethod
    def download_tweets_and_validate(cls, twitter, follower, follower_download_tweets, min_tweet_date,
                                     is_first_request, max_id=None):
        """ Download tweets. If there are not new results, return false to end the download. """
        download_tweets = cls.do_download_tweets_request(twitter, follower, is_first_request, max_id)
        if len(download_tweets) != 0:
            last_tweet = download_tweets[len(download_tweets) - 1]
            follower_download_tweets += download_tweets
            return cls.check_if_continue_downloading(last_tweet, min_tweet_date)
        return False

    @classmethod
    def do_download_tweets_request(cls, twitter, follower, is_first_request, max_id=None):
        """ If is_first_request is True, max_id parameter is not included in the request. """
        tweets = []
        try:
            if is_first_request:
                tweets = twitter.get_user_timeline(user_id=follower, include_rts=True, count=MAX_TWEETS)
            else:
                tweets = twitter.get_user_timeline(user_id=follower, include_rts=True, count=MAX_TWEETS,
                                                   max_id=max_id)
        except TwythonError as error:
            if error.error_code == PRIVATE_USER_ERROR_CODE:
                cls.get_logger().warning(f'User with id {follower} is private.')
                cls.update_follower_as_private(follower)
            else:
                cls.get_logger().error(
                    f'An unknown error occurred while trying to download tweets from: {follower}.')
                cls.get_logger().error(error)
        except TwythonRateLimitError:
            cls.get_logger().warning('Tweets download limit reached. Waiting.')
            # TODO ver que hacer cuando se alcanza el limite
        return tweets

    @classmethod
    def update_follower_as_private(cls, follower):
        # Retrieve the follower from DB
        raw_follower = RawFollowerDAO().get(follower)
        RawFollowerDAO().tag_as_private(raw_follower)

    @classmethod
    def update_follower(cls, follower):
        today = datetime.today()
        # Retrieve the follower from DB
        raw_follower = RawFollowerDAO().get(follower)
        raw_follower['download_on'] = today
        RawFollowerDAO().put(raw_follower)

    @classmethod
    def check_if_continue_downloading(cls, last_tweet, min_tweet_date):
        """" Return True if the oldest download's tweet is greater than min_date required. """
        last_tweet_date = datetime.datetime.strptime(last_tweet['created_at'], '%a %b %d %H:%M:%S %z %Y') \
            .astimezone(pytz.timezone('America/Argentina/Buenos_Aires'))
        return min_tweet_date < last_tweet_date

    @classmethod
    def store_new_tweets(cls, follower, follower_download_tweets, min_tweet_date):
        cls.get_logger().info(f'Storing new tweets of {follower}.')
        for tweet in follower_download_tweets:
            tweet_date = tweet['created_at_datetime'] = datetime.datetime.strptime(tweet['created_at'],
                                                                                   '%a %b %d %H:%M:%S %z %Y').astimezone(
                pytz.timezone('America/Argentina/Buenos_Aires'))
            if tweet_date >= min_tweet_date:
                raw_tweet = RawTweet(**{'id': tweet['id'],
                                        'created_at': tweet_date,
                                        'text': tweet['text'],
                                        'user_id': tweet['user']['id']})
                # TODO usar RawTweetDAO

    @classmethod
    def twitter(cls, credential):
        """ Create Twython instance depending on credential data. """
        if credential.access_token is None:
            twitter = Twython(app_key=credential.consumer_key, app_secret=credential.consumer_secret)
        elif credential.consumer_key is None:
            twitter = Twython(oauth_token=credential.access_token, oauth_token_secret=credential.access_secret)
        else:
            twitter = Twython(app_key=credential.consumer_key, app_secret=credential.consumer_secret,
                              oauth_token=credential.access_token, oauth_token_secret=credential.access_secret)
        return twitter

    @classmethod
    def get_logger(cls):
        return Logger('FollowerUpdateService')
