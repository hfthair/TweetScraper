# -*- coding: utf-8 -*-
import logging
import json
import os

# for mysql
import mysql.connector
from mysql.connector import errorcode

from TweetScraper.items import Tweet, User, Following
from TweetScraper.utils import mkdirs


logger = logging.getLogger(__name__)

class SavetoMySQLPipeline(object):
    ''' pipeline that save data to mysql '''

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        return cls(settings)

    def __init__(self, settings):
        self.buffer_threadhold = 100
        self.buffer_tweet = {}
        self.buffer_user = {}
        self.buffer_following = {}

        # connect to mysql server
        host = settings['MYSQL_HOST']
        database = settings['MYSQL_DATABASE']
        user = settings['MYSQL_USER']
        pwd = settings.get('MYSQL_PASSWORD', None)
        if pwd is None:
            pwd = input("Mysql Password: ")
            print('please add MYSQL_PASSWORD in settings.py')
        self.cnx = mysql.connector.connect(user=user, password=pwd, host=host,
                                database=database, buffered=True)
        self.cursor = self.cnx.cursor()

        self.table_name_tweet = settings['MYSQL_TABLE_TWEET']
        self.table_name_user = settings['MYSQL_TABLE_USER']
        self.table_following = settings['MYSQL_TABLE_FOLLOWING']

        self.create_tables()

    def create_tables(self):
        create_table_tweet_query = "CREATE TABLE IF NOT EXISTS `" + self.table_name_tweet + "` (\
                `ID` CHAR(20) PRIMARY KEY,\
                `url` VARCHAR(140) NOT NULL,\
                `datetime` VARCHAR(22),\
                `text` VARCHAR(1024),\
                `user_id` CHAR(20) NOT NULL,\
                `usernameTweet` VARCHAR(20) NOT NULL, \
                `nbr_retweet` INT DEFAULT 0, \
                `nbr_favorite` INT DEFAULT 0, \
                `nbr_reply` INT DEFAULT 0, \
                `has_image` BOOLEAN DEFAULT 0, \
                `image` VARCHAR(255), \
                `has_video` BOOLEAN DEFAULT 0, \
                `video` VARCHAR(255), \
                `has_media` BOOLEAN DEFAULT 0, \
                `media` VARCHAR(255), \
                `is_reply` BOOLEAN DEFAULT 0, \
                `is_retweet` BOOLEAN DEFAULT 0 \
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
        create_table_user_query = "CREATE TABLE IF NOT EXISTS `" + self.table_name_user + "` (\
                `ID` CHAR(20) PRIMARY KEY,\
                `name` VARCHAR(140) NOT NULL,\
                `screen_name` VARCHAR(140) NOT NULL,\
                `avatar` VARCHAR(330) NOT NULL\
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
        create_following_query = "CREATE TABLE IF NOT EXISTS `" + self.table_following + "` ( \
                `ID` CHAR(20) NOT NULL, \
                `following_id` CHAR(20) NOT NULL, \
                `following_name` VARCHAR(140) NOT NULL DEFAULT '', \
                INDEX `index_id`(`ID`), \
                PRIMARY KEY (`ID`, `following_id`) \
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"

        try:
            logger.info("Creating table...")
            self.cursor.execute(create_table_tweet_query)
            self.cursor.execute(create_table_user_query)
            self.cursor.execute(create_following_query)
            self.cnx.commit()
        except mysql.connector.Error as err:
            logger.error(err.msg)
        else:
            logger.info("Successfully created table.")

    def insert_tweets(self, items):
        keys = ('ID', 'url', 'datetime', 'text', 'user_id', 'usernameTweet', 'nbr_retweet',
            'nbr_favorite', 'nbr_reply', 'has_image', 'image', 'has_video', 'video',
            'has_media', 'media', 'is_reply', 'is_retweet') #item.keys()

        insert_query =  "INSERT IGNORE INTO " + self.table_name_tweet + " (" + ', '.join(keys) + " )"
        insert_query += " VALUES ( " + ",".join(("%s",) * len(keys)) +  " )"

        # True -> 1, False -> 0
        vals = [[item[k]*1 for k in keys] for item in items]

        try:
            logger.debug("Inserting tweet bulk size {}".format(len(vals)))
            self.cursor.executemany(insert_query, vals)
            self.cnx.commit()
        except mysql.connector.Error as err:
            logger.error(err.msg)
        else:
            logger.debug("Successfully inserted.")

    def insert_users(self, items):
        insert_query =  "INSERT IGNORE INTO " + self.table_name_user + " (ID, name, screen_name, avatar)"
        insert_query += " VALUES ( %s, %s, %s, %s )"

        vals = [(item['ID'], item['name'], item['screen_name'], item['avatar']) for item in items]

        try:
            logger.debug("Inserting user bulk size {}".format(len(vals)))
            self.cursor.executemany(insert_query, vals)
            self.cnx.commit()
        except mysql.connector.Error as err:
            logger.error(err.msg)
        else:
            logger.debug("Successfully inserted.")

    def insert_followings(self, items):
        vals = [(item['ID'], item['following_id'], item['following_name']) for item in items]

        insert_query =  "INSERT IGNORE INTO " + self.table_following + \
                " (ID, following_id, following_name) VALUES ( %s, %s, %s )"

        try:
            logger.debug("Inserting following bulk size {}".format(len(vals)))
            self.cursor.executemany(insert_query, vals)
            self.cnx.commit()
        except mysql.connector.Error as err:
            logger.error(err.msg)
        else:
            logger.debug("Successfully inserted.")

    def process_item(self, item, spider):
        if isinstance(item, Tweet):
            self.buffer_tweet[item['ID']] = dict(item)
            logger.debug("Add tweet to buffer: {}".format(item['url']))
        elif isinstance(item, User):
            self.buffer_user[item['ID']] = dict(item)
            logger.debug("Add user to buffer: {}".format(item['name']))
        elif isinstance(item, Following):
            self.buffer_following[item['ID'] + '<==>' + item['following_id']] = dict(item)
            logger.debug("Add following to buffer: {} - {}".format(item['ID'], item['following_name']))

        if len(self.buffer_tweet) > self.buffer_threadhold:
            self.insert_tweets(self.buffer_tweet.values())
            self.buffer_tweet = {}
        if len(self.buffer_user) > self.buffer_threadhold:
            self.insert_users(self.buffer_user.values())
            self.buffer_user = {}
        if len(self.buffer_following) > self.buffer_threadhold:
            self.insert_followings(self.buffer_following.values())
            self.buffer_following = {}

    def close_spider(self, spider):
        logger.warning('Save buffered data before shutdown!')
        print("Don't any thing, saving buffered data!")
        self.insert_tweets(self.buffer_tweet.values())
        self.insert_users(self.buffer_user.values())
        self.insert_followings(self.buffer_following.values())
        logger.warning('Save buffered data done!')


class SaveToFilePipeline(object):
    ''' pipeline that save data to disk '''
    def __init__(self):
        from scrapy.conf import settings
        self.saveTweetPath = settings['SAVE_TWEET_PATH']
        self.saveUserPath = settings['SAVE_USER_PATH']
        mkdirs(self.saveTweetPath) # ensure the path exists
        mkdirs(self.saveUserPath)

    def process_item(self, item, spider):
        if isinstance(item, Tweet):
            savePath = os.path.join(self.saveTweetPath, item['ID'])
            if os.path.isfile(savePath):
                pass # simply skip existing items
                ### or you can rewrite the file, if you don't want to skip:
                # self.save_to_file(item,savePath)
                # logger.info("Update tweet:%s"%dbItem['url'])
            else:
                self.save_to_file(item,savePath)
                logger.debug("Add tweet:%s" %item['url'])

        elif isinstance(item, User):
            savePath = os.path.join(self.saveUserPath, item['ID'])
            if os.path.isfile(savePath):
                pass # simply skip existing items
                ### or you can rewrite the file, if you don't want to skip:
                # self.save_to_file(item,savePath)
                # logger.info("Update user:%s"%dbItem['screen_name'])
            else:
                self.save_to_file(item, savePath)
                logger.debug("Add user:%s" %item['screen_name'])
        else:
            logger.info("Item type is not recognized! type = %s" %type(item))

    def save_to_file(self, item, fname):
        ''' input: 
                item - a dict like object
                fname - where to save
        '''
        with open(fname,'w') as f:
            json.dump(dict(item), f)
