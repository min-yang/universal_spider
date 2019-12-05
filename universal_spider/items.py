# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field

class Webpage(Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    url = Field()
    text = Field()
    image_urls = Field()
    images = Field()
    file_urls = Field()
    files = Field()
