# Introduction #

Crawl tweets from [Twitter Search](https://twitter.com/search-home) (*do not need twitter account*)

Crawl following relationships from [Follow Page](https://twitter.com/name??/following) (*twitter account needed*)

*part of this project is based on [jonbakerfish/TweetScraper](https://github.com/jonbakerfish/TweetScraper)*

# Dependence #
* [Scrapy](http://scrapy.org/) 
* [mysql-connector-python](https://dev.mysql.com/downloads/connector/python/)
* [js2py](https://pypi.org/project/Js2Py/)

# Spiders #
1. Search Spider: 

	Crawl tweets from url [Twitter Search](https://twitter.com/search-home) which does not require login twitter account

	*this spider is based on [jonbakerfish/TweetScraper](https://github.com/jonbakerfish/TweetScraper)*

		scrapy crawl search -a query="foo,#bar"

	where `query` is a list of keywords seperated by comma and quoted by `"`. The query can be any thing (keyword, hashtag, etc.) you want to search in [Twitter Search](https://twitter.com/search-home). `Search Spider` will crawl the search results of the query and save the tweet content and user information. You can also use the `operators` from [Twitter Search Page](https://twitter.com/search-home) in each query.

	#### Other parameters
	* `crawl_user[DEFAULT=True]`, if you do not want to crawl the author's of tweets in the same time
	* `limit[default=None]`, end the spider when reach the limit

		E.g.:

		```
		scrapy crawl search -a query=foo -a crawl_user=False
		```

	* you can use JOBDIR parameter so that you can pause/resume crawls
		```
		scrapy crawl search -a query=foo -s JOBDIR=dirname
		```
		Note: *don't press ctrl+C more than once if you want the progress to be saved*

2. Following Spider: 

	Crawl the users followed by the author of tweets crawled by Search Spider, the [URL](https://twitter.com/name??/following) requires login twitter account.

		scrapy crawl following

	*twitter account should be configured in settings.py*

	*the progress will be saved to a pickle file by default, don't press ctrl+C multiple times*

3. runner

	runner.py is used to crawl history of tweets from users crawled by Search Spider

		python TweetScraper/runner.py 500

4. unfinished feature

	[crawl_user_with_api.py](https://github.com/hfthair/TweetScraper/blob/master/TweetScraper/crawl_user_with_api.py)

	Requires:
	* [requests](https://pypi.org/project/requests/)
	* [pySocks](https://pypi.org/project/PySocks/)

	Todo:
	* time rate limits of twitter api

# Settings #

* Mysql
* twitter account

# Query Operators #


| Operator | Finds tweets... |
| --- | --- |
| twitter search | containing both "twitter" and "search". This is the default operator. |
| **"** happy hour **"** | containing the exact phrase "happy hour". |
| love **OR** hate | containing either "love" or "hate" (or both). |
| beer **-** root | containing "beer" but not "root". |
| **#** haiku | containing the hashtag "haiku". |
| **from:** alexiskold | sent from person "alexiskold". |
| **to:** techcrunch | sent to person "techcrunch". |
| **@** mashable | referencing person "mashable". |
| "happy hour" **near:** "san francisco" | containing the exact phrase "happy hour" and sent near "san francisco". |
| **near:** NYC **within:** 15mi | sent within 15 miles of "NYC". |
| superhero **since:** 2010-12-27 | containing "superhero" and sent since date "2010-12-27" (year-month-day). |
| ftw **until:** 2010-12-27 | containing "ftw" and sent up to date "2010-12-27". |
| movie -scary **:)** | containing "movie", but not "scary", and with a positive attitude. |
| flight **:(** | containing "flight" and with a negative attitude. |
| traffic **?** | containing "traffic" and asking a question. |
| hilarious **filter:links** | containing "hilarious" and linking to URLs. |
| news **source:twitterfeed** | containing "news" and entered via TwitterFeed |

# Acknowledgement #
Private project for self use

# Todo #
* rename folders, spiders and runner
* move twitter login part from spider to base
* a better way of pause/resume
