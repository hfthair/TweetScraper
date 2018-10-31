import logging
import traceback
import json
import oauth2 as oauth
import urllib
import httplib2
import socks
import mysql.connector

from mysql.connector import errorcode
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging

logger = logging.getLogger(__name__)

CONSUMER_KEY = ""
CONSUMER_SECRET = ""
ACCESS_KEY = ""
ACCESS_SECRET = ""

class Twitter:
    def __init__(self, enable_proxy=False):
        consumer = oauth.Consumer(key=CONSUMER_KEY, secret=CONSUMER_SECRET)
        access_token = oauth.Token(key=ACCESS_KEY, secret=ACCESS_SECRET)
        self.client = oauth.Client(consumer, access_token)
        if enable_proxy:
            self.client.proxy_info = httplib2.ProxyInfo(socks.PROXY_TYPE_HTTP, 'localhost', 1080)

    def get_friends(self, ID):
        url = "https://api.twitter.com/1.1/friends/ids.json?"
        param = {
            # 'screen_name': 'Jingjin60092590',
            'user_id': ID,
            'cursor': -1,
            'stringify_ids': 'true',
            'count': 1024
        }

        cursor = -1
        friends = []
        while cursor != 0:
            param['cursor'] = cursor
            # todo: exception
            _, data = self.client.request(url + urllib.parse.urlencode(param))
            resj = json.loads(data)
            print(json.dumps(resj, indent=4))
            ids = resj['ids']
            cursor = resj['next_cursor']
            friends.extend(ids)
        return friends

if __name__ == '__main__':
    tw = Twitter(enable_proxy=True)

    settings = get_project_settings()
    database = settings.get('MYSQL_DATABASE')
    user = settings.get('MYSQL_USER')
    pwd = settings.get('MYSQL_PASSWORD', None)
    if not pwd:
        pwd = input('please input password for {} @database: '.format(user))
    else:
        print('use password in settings.py')
    cnx = mysql.connector.connect(user=user, password=pwd,
                            host='localhost',
                            database=database, buffered=True)
    cursor = cnx.cursor()

    table_relationship = 'relationship'
    create_relationship_query =   "CREATE TABLE IF NOT EXISTS `" + table_relationship + "` ( \
            `ID` CHAR(20) NOT NULL, \
            `friend_id` CHAR(20) NOT NULL, \
            INDEX `index_id`(`ID`) \
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
    try:
        cursor.execute(create_relationship_query)
        cnx.commit()
    except mysql.connector.Error as err:
        print(err.msg)
    else:
        print("Successfully created table.")

    table_user = settings.get('MYSQL_TABLE_USER')
    query = "SELECT ID, name FROM {};".format(table_user)
    cursor.execute(query)

    scrawl_count = 0
    skip_count = 0
    fail_count = 0
    for ID, name in cursor.fetchall():
        print('crawl ID {} name {} ...'.format(ID, name))

        # check if crawled
        try:
            cursor.execute("SELECT ID FROM {} WHERE ID = %s".format(table_relationship), (ID, ))
            if cursor.fetchone():
                print('skip!')
                skip_count = skip_count + 1
                continue
        except:
            traceback.print_exc()

        friends = tw.get_friends(ID)
        print('friends count = {}'.format(len(friends)))
        query = "INSERT INTO {} (ID, friend_id) VALUES (%s, %s)".format(table_relationship)
        try:
            for i in friends:
                cursor.execute(query, (ID, i))
            cnx.commit()
        except:
            fail_count = fail_count + 1
            traceback.print_exc()
        else:
            scrawl_count = scrawl_count + 1

    print('Done. ===> finished {} | failed {} | skipped: {}.'.format(scrawl_count, fail_count, skip_count))


