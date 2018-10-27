from scrapy.spiders import CrawlSpider, Rule
from scrapy.selector import Selector
from scrapy.conf import settings
from scrapy import http
from scrapy.shell import inspect_response  # for debugging
import re
import json
import time
import logging
try:
    from urllib import quote  # Python 2.X
except ImportError:
    from urllib.parse import quote  # Python 3+

from datetime import datetime

from TweetScraper.items import Tweet, User

logger = logging.getLogger(__name__)


class TweetScraper(CrawlSpider):
    name = 'TweetScraper'
    allowed_domains = ['twitter.com']

    def __init__(self, query, save_user=True):
        self.url = "https://twitter.com/i/search/timeline?vertical=default" + \
                "&q=%s&src=typd&include_available_features=1&include_entities=1" + \
                "&lang=en&max_position=%s&reset_error_state=false"
        # if not top_tweet:
        #     self.url = self.url + "&f=tweets"
        self.query = query
        self.crawl_user = save_user

    def start_requests(self):
        url = self.url % (quote(self.query), '')
        yield http.Request(url, callback=self.parse_page)

    def parse_page(self, response):
        # handle current page
        data = json.loads(response.body.decode("utf-8"))
        for item in self.parse_tweets_block(data['items_html']):
            yield item

        # get next page
        min_position = data['min_position']
        url = self.url % (quote(self.query), quote(min_position))
        yield http.Request(url, callback=self.parse_page) #, meta={'proxy': '127.0.0.1:1081'}

    def parse_tweets_block(self, html_page):
        page = Selector(text=html_page)

        ### for text only tweets
        items = page.xpath('//li[@data-item-type="tweet"]/div')
        for item in self.parse_tweet_item(items):
            yield item

    def parse_tweet_item(self, items):
        for item in items:
            try:
                tweet = Tweet()

                tweet['usernameTweet'] = item.xpath(
                    './/span[@class="username u-dir u-textTruncate"]/b/text()').extract_first(default='')

                ID = item.xpath('.//@data-tweet-id').extract_first()
                if not ID:
                    continue
                tweet['ID'] = ID

                ### get text content
                tweet['text'] = ' '.join(
                    item.xpath('.//div[@class="js-tweet-text-container"]/p//text()').extract()).replace(' # ',
                                                                                                        '#').replace(
                    ' @ ', '@')
                if tweet['text'] == '':
                    # If there is not text, we ignore the tweet
                    continue

                ### get meta data
                tweet['url'] = item.xpath('.//@data-permalink-path').extract_first(default='')

                tweet['nbr_retweet'] = item.css('span.ProfileTweet-action--retweet > span.ProfileTweet-actionCount').xpath(
                    '@data-tweet-stat-count').extract_first(default=0)

                tweet['nbr_favorite'] = item.css('span.ProfileTweet-action--favorite > span.ProfileTweet-actionCount').xpath(
                    '@data-tweet-stat-count').extract_first(default=0)

                tweet['nbr_reply'] = item.css('span.ProfileTweet-action--reply > span.ProfileTweet-actionCount').xpath(
                    '@data-tweet-stat-count').extract_first(default=0)

                tweet['datetime'] = datetime.fromtimestamp(int(
                    item.xpath('.//div[@class="stream-item-header"]/small[@class="time"]/a/span/@data-time').extract()[
                        0])).strftime('%Y-%m-%d %H:%M:%S')

                tweet['has_image'] = False
                tweet['image'] = ''
                tweet['has_video'] = False
                tweet['video'] = ''
                tweet['has_media'] = False
                tweet['media'] = ''
                ### get photo
                has_cards = item.xpath('.//@data-card-type').extract()
                if has_cards and has_cards[0] == 'photo':
                    tweet['has_image'] = True
                    tweet['image'] = item.xpath('.//*/div/@data-image-url').extract_first(default='')
                elif has_cards:
                    logger.debug('Not handle "data-card-type":\n%s' % item.xpath('.').extract()[0])

                ### get animated_gif
                has_cards = item.xpath('.//@data-card2-type').extract()
                if has_cards:
                    if has_cards[0] == 'animated_gif':
                        tweet['has_video'] = True
                        tweet['video'] = item.xpath('.//*/source/@video-src').extract_first(default='')
                    elif has_cards[0] == 'player':
                        tweet['has_media'] = True
                        tweet['media'] = item.xpath('.//*/div/@data-card-url').extract_first(default='')
                    elif has_cards[0] == 'summary_large_image':
                        tweet['has_media'] = True
                        tweet['media'] = item.xpath('.//*/div/@data-card-url').extract_first(default='')
                    elif has_cards[0] == 'amplify':
                        tweet['has_media'] = True
                        tweet['media'] = item.xpath('.//*/div/@data-card-url').extract_first(default='')
                    elif has_cards[0] == 'summary':
                        tweet['has_media'] = True
                        tweet['media'] = item.xpath('.//*/div/@data-card-url').extract_first(default='')
                    elif has_cards[0] == '__entity_video':
                        pass  # TODO
                        # tweet['has_media'] = True
                        # tweet['medias'] = item.xpath('.//*/div/@data-src').extract()
                    else:  # there are many other types of card2 !!!!
                        logger.debug('Not handle "data-card2-type"')

                is_reply = item.xpath('.//div[@class="ReplyingToContextBelowAuthor"]').extract()
                tweet['is_reply'] = is_reply != []

                is_retweet = item.xpath('.//span[@class="js-retweet-text"]').extract()
                tweet['is_retweet'] = is_retweet != []

                tweet['user_id'] = item.xpath('.//@data-user-id').extract_first(default='')
                yield tweet

                if self.crawl_user:
                    ### get user info
                    user = User()
                    user['ID'] = tweet['user_id']
                    user['screen_name'] = item.xpath('.//@data-name').extract_first(default='')
                    user['name'] = item.xpath('.//@data-screen-name').extract_first(default='')
                    user['avatar'] = \
                        item.xpath('.//div[@class="content"]/div[@class="stream-item-header"]/a/img/@src').\
                            extract_first(default='')
                    yield user
            except:
                logger.error("Error tweet:\n")

