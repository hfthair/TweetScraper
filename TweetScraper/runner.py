import logging
import traceback
import mysql.connector

from multiprocessing import Process, Queue
from mysql.connector import errorcode
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging

# this will init env, we have to call this before import spider, or there will be import error
settings = get_project_settings()

from spiders.TweetCrawler import TweetScraper


def start_runner_inner(setti, name, q):
    try:
        # settings
        runner = CrawlerProcess(setti)
        runner.crawl(TweetScraper, query='from:{}'.format(name), save_user=False)
        runner.start()
        q.put(None)
    except Exception as e:
        q.put(e)

if __name__ == '__main__':

    database = settings.get('MYSQL_DATABASE')
    user = settings.get('MYSQL_USER')
    pwd = settings.get('MYSQL_PASSWORD', None)
    if not pwd:
        pwd = input('please input password for {} @database: '.format(user))
        # mark: use setting of spider at from_crawl in piplines.py so that this will work
        settings.set('MYSQL_PASSWORD', pwd, 'spider')
    else:
        print('use password in settings.py')
    cnx = mysql.connector.connect(user=user, password=pwd,
                            host='localhost',
                            database=database, buffered=True)
    cursor = cnx.cursor()

    table_mark_name = 'temp_user_mark'

    # create talbe if not exists
    create_table_mark_query =   "CREATE TABLE IF NOT EXISTS `" + table_mark_name + "` (\
            `ID` CHAR(20) PRIMARY KEY,\
            `name` VARCHAR(140) NOT NULL\
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
    try:
        cursor.execute(create_table_mark_query)
        cnx.commit()
    except mysql.connector.Error as err:
        print(err.msg)
    else:
        print("Successfully created table.")

    table_all_tweets = 'history_tweet'
    # todo: not working
    settings.set('MYSQL_TABLE_TWEET', table_all_tweets, 'spider')
    configure_logging(settings)

    table_user = settings.get('MYSQL_TABLE_USER')
    query = "SELECT ID, name FROM {};".format(table_user)
    cursor.execute(query)

    def start_runner(name):
        q = Queue()
        p = Process(target=start_runner_inner, args=(settings, name, q))
        p.start()
        res = q.get()
        p.join()
        if res:
            raise res

    scrawl_count = 0
    skip_count = 0
    fail_count = 0
    for ID, name in cursor.fetchall():
        print('crawl ID {} name {} ...'.format(ID, name))

        # check if crawled
        try:
            cursor.execute("SELECT ID FROM {} WHERE ID = %s".format(table_mark_name), (ID, ))
            if cursor.fetchone():
                print('skip!')
                skip_count = skip_count + 1
                continue
        except:
            traceback.print_exc()

        try:
            start_runner(name)

            cursor.execute("INSERT INTO {} (ID, name) VALUES (%s, %s)".format(table_mark_name), (ID, name))
            cnx.commit()
        except:
            fail_count = fail_count + 1
            traceback.print_exc()
        else:
            scrawl_count = scrawl_count + 1
        print('finish {}'.format(name))

    print('Done. ===> finished {} | failed {} | skipped: {}.'.format(scrawl_count, fail_count, skip_count))
    # todo: remove temp table if no fail

