'''
this is a runner which will crawl history tweets of all users in table user.
this runner will call the spider |Search Spider|.
history tweets will be saved in table |history_tweet|.
limit can be set, usage:
    python runner.py limit[int]
'''
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

from spiders.search import SearchSpider

table_all_tweets = 'history_tweet'

def start_runner_inner(setti, name, limit, q):
    try:
        # settings
        runner = CrawlerProcess(setti)
        runner.crawl(SearchSpider, query='from:{}'.format(name), save_user=False, limit=limit)
        runner.start()
        q.put(None)
    except Exception as e:
        q.put(e)

if __name__ == '__main__':
    import os
    import pickle
    import sys
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    pickle_name = '{}.pickle'.format(os.path.basename(__file__))

    i = input('Crawl history tweets with {} limits? (y/n)'.format(
        'NO' if limit is None else limit))
    if i.lower() != 'y':
        print('User cancelled!')
        sys.exit(0)

    finished = set()
    if os.path.isfile(pickle_name):
        i = input('Progress file detected, load to current runner? (y/n) ')
        if i.lower() == 'y':
            with open(pickle_name, 'rb') as f:
                finished = pickle.load(f)
        else:
            i = input('Are you sure you want to ignore? (y/n) ')
            if i.lower() != 'y':
                sys.exit(0)

    database = settings.get('MYSQL_DATABASE')
    user = settings.get('MYSQL_USER')
    pwd = settings.get('MYSQL_PASSWORD', None)
    if pwd is None:
        pwd = input('please input password for {} @database: '.format(user))
        # mark: use setting of spider at from_crawl in piplines.py so that this will work
        settings.set('MYSQL_PASSWORD', pwd, 'spider')
    else:
        print('use password in settings.py')
    cnx = mysql.connector.connect(user=user, password=pwd,
                            host='localhost',
                            database=database, buffered=True)
    cursor = cnx.cursor()

    settings.set('MYSQL_TABLE_TWEET', table_all_tweets, 'spider')
    configure_logging(settings)

    table_user = settings.get('MYSQL_TABLE_USER')
    query = "SELECT ID, name FROM {};".format(table_user)
    cursor.execute(query)

    def start_runner(name, limit):
        q = Queue()
        p = Process(target=start_runner_inner, args=(settings, name, limit, q))
        try:
            p.start()
            res = q.get()
            p.join()
            if res:
                raise res
        except KeyboardInterrupt as e:
            p.terminate()
            print('Terminated by user.')
            raise e

    total = cursor.rowcount
    scrawl_count = 0
    skip_count = 0
    fail_count = 0
    for ID, name in cursor.fetchall():
        curr = scrawl_count + skip_count + fail_count + 1
        print('[{}/{}] Crawl ID {} name {} ...'.format(curr, total, ID, name))

        try:
            # check if crawled
            if ID in finished:
                print('alread crawled, skip!')
                skip_count = skip_count + 1
                continue

            start_runner(name, limit)

            finished.add(ID)
            with open(pickle_name, 'wb') as f:
                pickle.dump(finished, f)
        except KeyboardInterrupt:
            sys.exit(-1)
        except:
            fail_count = fail_count + 1
            traceback.print_exc()
        else:
            scrawl_count = scrawl_count + 1
        print('finish {}'.format(name))

    print('Done. ===> finished {} | failed {} | skipped: {}.'.format(scrawl_count, fail_count, skip_count))
