# -*- coding: utf-8 -*-
import logging
import js2py
import json
import re

import mysql.connector
from mysql.connector import errorcode

from scrapy import http
from scrapy.selector import Selector
from scrapy.spiders import CrawlSpider
from urllib.parse import urlencode

from TweetScraper.items import Following

from scrapy.shell import inspect_response  # for debugging

logger = logging.getLogger(__name__)

class UserCrawlerSpider(CrawlSpider):
    name = 'following_crawler'
    allowed_domains = ['twitter.com']

    # I don't want my account to be locked
    custom_settings = {
        'DOWNLOAD_DELAY ': '0.25',
    }

    def start_requests(self):
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

        formdata = {
            'session[username_or_email]': 'zhang96084371',
            'session[password]': 'nicaicai',
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

        for ID, name in cursor.fetchall():
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



