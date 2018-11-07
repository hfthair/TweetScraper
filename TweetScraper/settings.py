# -*- coding: utf-8 -*-

# !!! # Crawl responsibly by identifying yourself (and your website/e-mail) on the user-agent
# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# settings for spiders
BOT_NAME = 'TweetScraper'
LOG_LEVEL = 'INFO'
DOWNLOAD_HANDLERS = {'s3': None,} # from http://stackoverflow.com/a/31233576/2297751, TODO
LOG_FILE = 'info.log'

SPIDER_MODULES = ['TweetScraper.spiders']
NEWSPIDER_MODULE = 'TweetScraper.spiders'
ITEM_PIPELINES = {
    # 'TweetScraper.pipelines.SaveToFilePipeline':100,
    #'TweetScraper.pipelines.SaveToMongoPipeline':100, # replace `SaveToFilePipeline` with this to use MongoDB
    'TweetScraper.pipelines.SavetoMySQLPipeline':100, # replace `SaveToFilePipeline` with this to use MySQL
}

# CONCURRENT_REQUESTS = 16

SPIDER_FOLLOWING_LIMIT = 2000

# settings for where to save data on disk
SAVE_TWEET_PATH = './Data/tweet/'
SAVE_USER_PATH = './Data/user/'

# for mysql
MYSQL_HOST = 'localhost'
MYSQL_DATABASE = 'tweets'
MYSQL_USER = 'zhang'
MYSQL_PASSWORD = None
MYSQL_TABLE_TWEET = 'tweet'
MYSQL_TABLE_USER = 'user'
MYSQL_TABLE_FOLLOWING = 'following'

# for twitter login
TWITTER_ACCOUNT = 'zhang96084371'
TWITTER_PASSWORD = None

# # settings for mongodb
# MONGODB_SERVER = "127.0.0.1"
# MONGODB_PORT = 27017
# MONGODB_DB = "TweetScraper"        # database name to save the crawled data
# MONGODB_TWEET_COLLECTION = "tweet" # collection name to save tweets
# MONGODB_USER_COLLECTION = "user"   # collection name to save users


