from uuid import uuid4
from collections import OrderedDict
from os.path import abspath, join, dirname

from datetime import timedelta

from src.db.dao.CooccurrenceDAO import CooccurrenceDAO
from src.db.dao.RawTweetDAO import RawTweetDAO
from src.exception.NoHashtagCooccurrenceError import NoHashtagCooccurrenceError
from src.util.FileUtils import FileUtils
from src.util.logging.Logger import Logger


class HashtagCooccurrenceService:
    DIR_PATH = f"{abspath(join(dirname(__file__), '../../'))}/resources/cooccurrence"
    THIRTY_ONE_BITS = 0x7fffffff

    @classmethod
    def export_counts_for_time_window(cls, start_date, end_date):
        """ Count appearances of each pair of hashtags in the given time window and export to .txt file. """
        if end_date is None or start_date.date() == end_date.date():
            end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
        cls.get_logger().info(f'Starting hashtag cooccurrence counting for window starting on {start_date}'
                              f' and ending on {end_date}')
        counts = dict()
        ids = dict()
        # Retrieve from database
        documents = CooccurrenceDAO().find_in_window(start_date, end_date)
        # Iterate and count
        for document in documents:
            cls.__add_to_counts(counts, document['pair'])
            cls.__add_to_ids(ids, document['pair'])
        # Throw exception if there were no documents found
        if len(counts) == 0:
            raise NoHashtagCooccurrenceError(start_date, end_date)
        # Write weights file
        file_name = cls.__make_file_name('weights', start_date, end_date)
        with open(f'{cls.DIR_PATH}/{file_name}', 'w') as fd:
            # Write a line for each pair of hashtags
            for pair, count in OrderedDict(sorted(counts.items(), key=lambda item: item[1], reverse=True)).items():
                pair = pair.split('-')
                fd.write(f'{ids[pair[0]]} {ids[pair[1]]} {count}\n')
        cls.get_logger().info(f'Counting result was written in file {file_name}')
        # Write id reference file
        file_name = cls.__make_file_name('ids', start_date, end_date)
        with open(f'{cls.DIR_PATH}/{file_name}', 'w') as fd:
            # Write a line for each hashtag
            for hashtag, uuid in ids.items():
                fd.write(f'{hashtag} {uuid}\n')
        cls.get_logger().info(f'Hashtag ids were written in file {file_name}')

    @classmethod
    def process_tweet(cls, tweet):
        """ Process tweet for hashtag cooccurrence detection. """
        if cls.__is_processable(tweet):
            # Flatten list of hashtags and keep distinct values only
            hashtags = list({h['text'].lower() for h in tweet['entities']['hashtags']})
            # Generate documents for cooccurrence collection and store
            for i in range(len(hashtags) - 1):
                for j in range(i + 1, len(hashtags)):
                    # Store in database
                    CooccurrenceDAO().store(tweet, sorted([hashtags[i], hashtags[j]]))
        # Mark tweet as already used
        RawTweetDAO().cooccurrence_checked(tweet)

    @classmethod
    def __is_processable(cls, tweet):
        """ Verify if this tweet has the characteristics to bo analyzed for hashtag cooccurrence.
        Cooccurrence calculation is only possible if it is not a retweet and has at least 2 hashtags.
        The upper bound is arbitrary."""
        return not tweet.get('retweeted_status', None) and 1 < len(tweet['entities']['hashtags']) < 8

    @classmethod
    def __add_to_counts(cls, counts, pair):
        """ Add entry to map if it doesn't exists and add 1."""
        key = f'{pair[0]}-{pair[1]}'
        if key not in counts:
            counts[key] = 0
        counts[key] += 1

    @classmethod
    def __add_to_ids(cls, ids, pair):
        """ Add entry to map if it doesn't exist. Hashtag ids are unique UUIDs. """
        for hashtag in pair:
            if hashtag not in ids:
                # Get only first 32 bits of uuid. Just to avoid OSLOM's explosion
                ids[hashtag] = uuid4().int & cls.THIRTY_ONE_BITS

    @classmethod
    def __make_file_name(cls, file_id, start_date, end_date):
        """ Create file name for .txt exporting. """
        return FileUtils.file_name_with_dates(file_id, start_date, end_date, '.txt')

    @classmethod
    def get_logger(cls):
        return Logger('HashtagCooccurrenceService')
