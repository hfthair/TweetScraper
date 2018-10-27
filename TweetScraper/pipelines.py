# -*- coding: utf-8 -*-
from scrapy.exceptions import DropItem
from scrapy.conf import settings
import logging
import json
import os

# for mysql
import mysql.connector
from mysql.connector import errorcode

from TweetScraper.items import Tweet, User
from TweetScraper.utils import mkdirs


logger = logging.getLogger(__name__)

class SavetoMySQLPipeline(object):

    ''' pipeline that save data to mysql '''
    def __init__(self):
        # connect to mysql server
        host = settings['MYSQL_HOST']
        database = settings['MYSQL_DATABASE']
        user = settings['MYSQL_USER']
        pwd = ''
        if 'MYSQL_PASSWORD' in settings:
            pwd = settings['MYSQL_PASSWORD']
        else:
            pwd = input("Password: ")
        self.cnx = mysql.connector.connect(user=user, password=pwd, host=host,
                                database=database, buffered=True)
        self.cursor = self.cnx.cursor()
        self.table_name_tweet = settings['MYSQL_TABLE_TWEET']
        self.table_name_user = settings['MYSQL_TABLE_USER']
        create_table_tweet_query =   "CREATE TABLE IF NOT EXISTS `" + self.table_name_tweet + "` (\
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
        create_table_user_query =   "CREATE TABLE IF NOT EXISTS `" + self.table_name_user + "` (\
                `ID` CHAR(20) PRIMARY KEY,\
                `name` VARCHAR(140) NOT NULL,\
                `screen_name` VARCHAR(140) NOT NULL,\
                `avatar` VARCHAR(330) NOT NULL\
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"

        try:
            logger.info("Creating table...")
            self.cursor.execute(create_table_tweet_query)
            self.cursor.execute(create_table_user_query)
            self.cnx.commit()
        except mysql.connector.Error as err:
            logger.error(err.msg)
        else:
            logger.info("Successfully created table.")

    def find_one(self, table, value):
        select_query =  "SELECT ID FROM " + table + " WHERE ID = " + value + ";"
        try:
            self.cursor.execute(select_query)
        except mysql.connector.Error as err:
            return False

        if (self.cursor.fetchone() == None):
            return False
        else:
            return True

    def insert_tweet(self, item):

        keys = ('ID', 'url', 'datetime', 'text', 'user_id', 'usernameTweet', 'nbr_retweet',
            'nbr_favorite', 'nbr_reply', 'has_image', 'image', 'has_video', 'video',
            'has_media', 'media', 'is_reply', 'is_retweet') #item.keys()

        insert_query =  "INSERT INTO " + self.table_name_tweet + " (" + ', '.join(keys) + " )"
        insert_query += " VALUES ( " + ",".join(("%s",) * len(keys)) +  " )"

        # True -> 1, False -> 0
        vals = [item[k]*1 for k in keys]

        try:
            logger.debug("Inserting tweet {}...".format(item['ID']))
            self.cursor.execute(insert_query, vals)
            self.cnx.commit()
        except mysql.connector.Error as err:
            logger.error(err.msg)
        else:
            logger.debug("Successfully inserted.")

    def insert_user(self, item):
        ID = item['ID']
        name = item['name']
        screen_name = item['screen_name']
        avatar = item['avatar']

        insert_query =  "INSERT INTO " + self.table_name_user + " (ID, name, screen_name, avatar)"
        insert_query += " VALUES ( %s, %s, %s, %s )"

        vals = (ID, name, screen_name, avatar)

        try:
            logger.debug("Inserting user {}...".format(ID))
            self.cursor.execute(insert_query, vals)
            self.cnx.commit()
        except mysql.connector.Error as err:
            logger.error(err.msg)
        else:
            logger.debug("Successfully inserted.")


    def process_item(self, item, spider):
        if isinstance(item, Tweet):
            dbItem = self.find_one(self.table_name_tweet, item['ID'])
            if dbItem:
                logger.debug("tweet already exists:%s" %item['url'])
            else:
                self.insert_tweet(dict(item))
                logger.debug("Add tweet:%s" %item['url'])
        elif isinstance(item, User):
            dbItem = self.find_one(self.table_name_user, item['ID'])
            if dbItem:
                logger.debug("user already exists:%s" %item['name'])
            else:
                self.insert_user(dict(item))
                logger.debug("Add user:%s" %item['name'])


class SaveToFilePipeline(object):
    ''' pipeline that save data to disk '''
    def __init__(self):
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
