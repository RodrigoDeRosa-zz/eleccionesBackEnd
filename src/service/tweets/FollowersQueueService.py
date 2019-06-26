import random
from datetime import datetime

from src.db.dao.RawFollowerDAO import RawFollowerDAO
from src.exception.NoMoreFollowersToUpdateTweetsError import NoMoreFollowersToUpdateTweetsError
from src.util.concurrency.ConcurrencyUtils import ConcurrencyUtils
from src.util.config.ConfigurationManager import ConfigurationManager
from src.util.logging.Logger import Logger
from src.util.meta.Singleton import Singleton
from src.util.slack.SlackHelper import SlackHelper


class FollowersQueueService(metaclass=Singleton):

    def __init__(self):
        self.logger = Logger(self.__class__.__name__)
        self.updating_followers = {}
        ConcurrencyUtils().create_lock('followers_for_update_tweets')

    def get_followers_to_update(self):
        # Acquire lock for get the followers
        ConcurrencyUtils().acquire_lock('followers_for_update_tweets')
        self.logger.info(f'Getting followers to update their tweets. Queue\'s size: {len(self.updating_followers)} ')

        max_users_per_window = ConfigurationManager().get_int('max_users_per_window')
        followers_to_update = {}

        if len(self.updating_followers) <= 2 * max_users_per_window:
            # Retrieve more candidates from db
            self.add_followers_to_be_updated()

        if len(self.updating_followers) == 0:
            SlackHelper().post_message_to_channel(
                "No se obtuvieron seguidores de la base de datos.")
            self.logger.error('There are not followers to update their tweets.')
            raise NoMoreFollowersToUpdateTweetsError()

        random_followers_keys = []
        try:
            random_followers_keys = random.sample(self.updating_followers.keys(), max_users_per_window)
        except ValueError:
            SlackHelper().post_message_to_channel(
                "Quedan pocos usuarios por actualizar en la cola.")
            self.logger.warning(f'There are {len(self.updating_followers)} followers to update in the queue.')
            random_followers_keys = self.updating_followers.copy()
            self.updating_followers = {}
            return random_followers_keys
        # Remove selected followers
        for follower in random_followers_keys:
            followers_to_update[follower] = self.updating_followers.pop(follower)

        ConcurrencyUtils().release_lock('followers_for_update_tweets')

        return followers_to_update

    def add_followers_to_be_updated(self):
        # TODO Analizar productor y consumidor en python.
        self.logger.info(
            f'Adding new followers to update their tweets. Actual size: {str(len(self.updating_followers))}')
        new_followers = RawFollowerDAO().get_random_followers_sample()
        if len(new_followers) == 0:
            # If there are no new results
            self.logger.error('Can\'t retrieve followers to update their tweets. ')
            raise NoMoreFollowersToUpdateTweetsError()
        self.updating_followers.update(new_followers)

    def add_last_downloaded_followers(self, private_users=200000):
        # TODO Borrar esto cuando se recorran todos los usuarios privados
        self.logger.info('Adding last downloaded followers')
        date = datetime(2019, 6, 24, 00, 00, 00)
        downloaded = RawFollowerDAO().get_with_limit({'$and': [
            {'is_private': True}, {'downloaded_on': {'$lt': date}}
        ]}, None, private_users)
        self.add_followers(downloaded)

        initDate = datetime(2019, 6, 17, 20, 0, 0)
        endDate = datetime(2019, 6, 19, 8, 0, 0)
        downloaded = RawFollowerDAO().get_all({
            '$and': [
                {"downloaded_on": {'$gt': initDate}},
                {"downloaded_on": {'$lt': endDate}},
                {'has_tweets': False}
            ]})
        self.add_followers(downloaded)

        # {'$and': [{"downloaded_on": {$gt: new ISODate("2019-06-17T20:00:00")}}, {"downloaded_on": {$lt: new ISODate("2019-06-19T08:00:00")}}, {'has_tweets': false} ]}

        initDate = datetime(2019, 6, 24, 0, 0, 0)
        endDate = datetime(2019, 6, 25, 0, 0, 0)
        downloaded = RawFollowerDAO().get_all({
            '$and': [
                {"downloaded_on": {'$gt': initDate}},
                {"downloaded_on": {'$lt': endDate}},
                {'has_tweets': None},
                {'is_private': True}
            ]})
        self.add_followers(downloaded)

        downloaded = RawFollowerDAO().get_with_limit({
            '$and': [
                {'has_tweets': {'$exists': False}},
                {'is_private': False}
            ]})
        self.add_followers(downloaded)
        self.logger.info('Finishing insertion of last downloaded followers')

    def add_followers(self, downloaded):
        followers = {}
        for follower in downloaded:
            followers[follower['_id']] = follower['last_tweet_date']
        self.logger.info(f"Added {len(followers)} to queue.")
        self.updating_followers.update(followers)
