# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request
from itemadapter import ItemAdapter
from pymongo import MongoClient


class GbParsePipeline:

    def __init__(self):
        self.db = MongoClient()['parser']

    def process_item(self, item, spider):
        collection = self.db[spider.name]
        collection.insert_one(item)
        return item


class GbImagesPipeline(ImagesPipeline):

    def get_media_requests(self, item, info):
        image = item.get('image', '')
        yield Request(image)

    def item_completed(self, results, item, info):
        # Заменяем ссылку на изображение результатом работы пайплайна
        item['image'] = [itm[1] for itm in results]
        return item
