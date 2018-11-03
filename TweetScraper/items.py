# -*- coding: utf-8 -*-

# Define here the models for your scraped items
from scrapy import Item, Field


class Tweet(Item):
    ID = Field()       # tweet id
    url = Field()      # tweet url
    datetime = Field() # post time
    text = Field()     # text content
    user_id = Field()  # user id
    usernameTweet = Field() # username of tweet

    nbr_retweet = Field()  # nbr of retweet
    nbr_favorite = Field() # nbr of favorite
    nbr_reply = Field()    # nbr of reply

    is_reply = Field()   # boolean if the tweet is a reply or not
    is_retweet = Field() # boolean if the tweet is just a retweet of another tweet

    has_image = Field() # True/False, whether a tweet contains images
    image = Field()     # a list of image urls, empty if none

    has_video = Field() # True/False, whether a tweet contains videos
    video = Field()     # a list of video urls

    has_media = Field() # True/False, whether a tweet contains media (e.g. summary)
    media = Field()     # a list of media


class User(Item):
    ID = Field()            # user id
    name = Field()          # twitter's screen_name(the name you can @)
    screen_name = Field()   # user name shown in bold on the profile card
    avatar = Field()        # avator url

class Following(Item):
    ID = Field()               # user id
    following_id = Field()     # id of following user
    following_name = Field()   # name of following user

