# -*- coding: utf-8 -*-
import logging
import os
import sys
import js2py
import json
import pickle
import re

import mysql.connector
from mysql.connector import errorcode

from scrapy import http
from scrapy import signals
from scrapy.selector import Selector
from scrapy.spiders import CrawlSpider
from urllib.parse import urlencode

from TweetScraper.items import Following

from scrapy.shell import inspect_response  # for debugging

logger = logging.getLogger(__name__)

class UserCrawlerSpider(CrawlSpider):
    name = 'following_crawler'
    allowed_domains = ['twitter.com']

    # # I don't want my account to be locked
    # custom_settings = {
    #     'DOWNLOAD_DELAY ': '0.25',
    # }

    def __init__(self, *a, **kw):
        super(UserCrawlerSpider, self).__init__(*a, **kw)
        self.finished = set()

        # load progress from pickle
        self.pickle_name = '{}.pickle'.format(self.name)
        if os.path.isfile(self.pickle_name):
            i = input('Progress file detected, load to current spider? (y/n)')
            if i.lower() == 'y':
                with open(self.pickle_name, 'rb') as f:
                    self.finished = pickle.load(f)
            else:
                i = input('You are sure you want to ignore? (y/n)')
                if i.lower() != 'y':
                    sys.exit(0)

    def start_requests(self):
        # can not connect in __init__ because crawler is not binded before construct
        self.crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)

        yield http.Request("https://twitter.com/login?lang=en", \
                        meta={'cookiejar': 1}, callback=self.pre_login)

    def pre_login(self, response):
        script_url = "https://twitter.com/i/js_inst?c_name=ui_metrics"
        yield http.Request(script_url, meta={'cookiejar': 1, 'response': response}, callback=self.login)

    def login(self, response):
        js_mock = '''
            e = { setAttribute:function(x,y){},appendChild:function(x){},removeChild:function(x){},innerText: ''}
            e["lastElementChild"]=e;e["parentNode"]=e;e["children"]=[e];
            document = { getElementsByTagName:function(x){return [e];},createElement:function(x){return e;}}
            '''
        js_func = response.text.split('\n')[2]
        js_context = js2py.EvalJs()
        js_context.execute(js_mock)
        js_context.execute(js_func)

        pattern = re.compile(r'function [a-zA-Z]+')
        js_func_name = re.search(pattern, js_func).group().replace('function ', '')

        js_context.execute('var ui_metrics = {}()'.format(js_func_name))

        account = self.settings.get('TWITTER_ACCOUNT')
        password = self.settings.get('TWITTER_PASSWORD', None)
        if not password:
            raise Exception('Please add TWITTER_PASSWORD to settings.py')

        formdata = {
            'session[username_or_email]': account,
            'session[password]': password,
            'ui_metrics': js_context.ui_metrics
        }

        resp = http.FormRequest.from_response(response.meta['response'], \
                    formxpath='//*[@id="page-container"]/div/div[1]/form', \
                    formdata=formdata, \
                    meta={'cookiejar': 1}, \
                    callback=self.redirect)
        yield resp

    def redirect(self, response):
        if 'New to Twitter?' not in response.text and 'Join Twitter today' not in response.text:
            logger.info('login success!')
        else:
            logger.error('login fail!')
            raise Exception('login fail')

        database = self.settings.get('MYSQL_DATABASE')
        user = self.settings.get('MYSQL_USER')
        pwd = self.settings.get('MYSQL_PASSWORD', None)
        if not pwd:
            pwd = input('please input password for {} @database: '.format(user))
            print('please add MYSQL_PASSWORD in settings.py')
        else:
            print('use password in settings.py')
        cnx = mysql.connector.connect(user=user, password=pwd,
                            host='localhost',
                            database=database, buffered=True)
        cursor = cnx.cursor()
        table_user = self.settings.get('MYSQL_TABLE_USER')
        cursor.execute("SELECT ID, name FROM {};".format(table_user))
        self.total_cnt = cursor.rowcount

        for ID, name in cursor.fetchall():
            if ID in self.finished:
                logger.info('{}/{} already crawled, skip!'.format(name, ID))
            else:
                yield self.gen_request(ID, name, self.parse)

    def gen_request(self, ID, name, callback, max_pos='-1'):
        data = {
            'include_available_features': '1',
            'include_entities': '0',
            'max_position': max_pos,
            'reset_error_state': 'false'
        }

        return http.Request("https://twitter.com/{}/following/users?".format(name) + urlencode(data), \
                        meta={'cookiejar': 1, 'ID': ID, 'name': name}, callback=callback)

    def parse(self, response):
        ID = response.meta['ID']
        data = json.loads(response.text)
        min_position = data['min_position']
        has_more = data['has_more_items']
        inner_html = data['items_html']
        _ = data['new_latent_count']

        page = Selector(text=inner_html)
        profile_cards = page.xpath(
            '//div[contains(concat(" ", normalize-space(@class), " "), " ProfileCard ")]')
        followings = (
            (card.xpath('@data-user-id').extract_first(),
             card.xpath('@data-screen-name').extract_first())
            for card in profile_cards)

        for fi, fn in followings:
            follow = Following()
            follow['ID'] = ID
            follow['following_id'] = fi
            follow['following_name'] = fn
            yield follow

        if has_more and min_position:
            yield self.gen_request(ID, response.meta['name'], self.parse, min_position)
        else:
            self.finished.add(ID)
            logger.info('[{}/{}] crawled user id.{} name.{} .'.format(len(self.finished),
                    self.total_cnt, ID, response.meta['name']))

    def spider_closed(self, spider, reason):
        logger.info('Spider closed, reason: {}'.format(reason))
        with open(self.pickle_name, 'wb') as f:
            pickle.dump(self.finished, f)

