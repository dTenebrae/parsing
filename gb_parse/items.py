# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class GbParseItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class HeadHuntersJobItem(scrapy.Item):
    _id = scrapy.Field()
    job_title = scrapy.Field()
    salary = scrapy.Field()
    description = scrapy.Field()
    tags = scrapy.Field()
    employer_url = scrapy.Field()


class HeadHunterCompanyItem(scrapy.Item):
    _id = scrapy.Field()
    company_name = scrapy.Field()
    company_url = scrapy.Field()
    company_desc = scrapy.Field()
    company_fields = scrapy.Field()
