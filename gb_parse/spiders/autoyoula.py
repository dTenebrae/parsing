import scrapy
import re
import base64
import pymongo


class AutoyoulaSpider(scrapy.Spider):
    name = 'autoyoula'
    allowed_domains = ['auto.youla.ru']
    start_urls = ['http://auto.youla.ru/']
    css_query = {
        'brands': '.TransportMainFilters_brandsList__2tIkv .ColumnItemList_container__5gTrc '
                  '.ColumnItemList_column__5gjdt a.blackLink',
        'pages': '.Paginator_block__2XAPy .Paginator_button__u1e7D',
        'models': 'article.SerpSnippet_snippet__3O1t2 a.SerpSnippet_name__3F7Yu',
        'model_title': '.AdvertCard_advertTitle__1S1Ak::text',
        'images': '.PhotoGallery_block__1ejQ1 .PhotoGallery_photo__36e_r img',
        'description': '.AdvertCard_descriptionInner__KnuRi::text',
        'spec_labels': '.AdvertCard_specs__2FEHc .AdvertSpecs_row__ljPcX .AdvertSpecs_label__2JHnS::text',
        'spec_data': '.AdvertCard_specs__2FEHc .AdvertSpecs_row__ljPcX .AdvertSpecs_data__xK2Qx *::text',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = pymongo.MongoClient()['parser'][self.name]

    def parse(self, response):
        for link in response.css(self.css_query['brands']):
            yield response.follow(link.attrib['href'], callback=self.brand_page_parse)

    def brand_page_parse(self, response):
        for page in response.css(self.css_query['pages']):
            yield response.follow(page.attrib['href'], callback=self.brand_page_parse)

        for model in response.css(self.css_query['models']):
            yield response.follow(model.attrib['href'], callback=self.ads_parse)

    def ads_parse(self, response):
        data = {
            'title': response.css(self.css_query['model_title']).get(),
            'images': [image.attrib['src'] for image in response.css(self.css_query['images'])],
            'description': response.css(self.css_query['description']).get(),
            'spec_dict': {label.get(): data.get() for label, data in zip(response.css(self.css_query['spec_labels']),
                                                                         response.css(self.css_query['spec_data']))},
            'author': '',
            'phone': ''
        }

        for item in response.css('script').extract():
            phone = re.findall('phone%22%2C%22(\w+)', item)
            if phone:
                data['phone'] = base64.b64decode(base64.b64decode(phone[0] + '==')).decode("utf-8")

            author_url = re.findall('youlaId%22%2C%22([a-z, 0-9]+)%22%2C%22avatar', item)
            if author_url:
                data['author'] = 'https://youla.ru/user/' + author_url[0]

        self.db.insert_one(data)
