import scrapy
import json
import datetime as dt
from ..items import InstagramPost, InstagramTag


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    allowed_domains = ['www.instagram.com']
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    graphql_url = '/graphql/query/'
    start_urls = ['https://www.instagram.com/']
    csrf_token = ''
    checked_tags = []
    query = {
        'posts': '56a7068fea504063273cc2120ffd54f3',
        'tags': "9b498c08113f1e09617a1703c22b2f32",
    }

    def __init__(self, login, password, start_tags: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.start_tags = [f'/explore/tags/{tag}/' for tag in start_tags]
        self.start_tags = [f'/explore/tags/{tag}/?__a=1' for tag in start_tags]
        self.login = login
        self.password = password

    @staticmethod
    def script_data(response) -> dict:
        return json.loads(response.xpath('//script[contains(text(),"window._sharedData")]/text()').get().replace(
            'window._sharedData = ', '').rstrip(';'))

    def parse(self, response, **kwargs):
        # авторизуемся
        try:
            data = self.script_data(response)
            yield scrapy.FormRequest(
                self.login_url,
                method='POST',
                callback=self.parse,
                formdata={
                    'username': self.login,
                    'enc_password': self.password
                },
                headers={
                    'X-CSRFToken': data['config']['csrf_token']
                }
            )
        except AttributeError:
            # Если вывалились в ошибку - есть шанс, что авторизовались
            data = response.json()
            if data['authenticated']:
                for tag in self.start_tags:
                    yield response.follow(tag, callback=self.json_parse)

    # Вариант с использованием api Instagram'a (В конец строки с тэгом или постом добавляем ?__a=1 - что дает нам JSON
    # ответ с нужными данными. Чтобы пройтись по пагинации - добавляем после этой строки &max_id={значение end cursor})
    def json_parse(self, response):
        js_data = response.json()
        # Находим хэш конца постов
        end_cursor = js_data['graphql']['hashtag']['edge_hashtag_to_media']['page_info']['end_cursor']

        # Сохраняем тэг в item(если он отсутствует в пройденых тэгах)
        tag = js_data["graphql"]["hashtag"]
        tag_name = tag['name']
        if tag_name not in self.checked_tags:
            self.checked_tags.append(tag_name)
            yield InstagramTag(
                date_parse=dt.datetime.utcnow(),
                data={
                    'id': tag['id'],
                    'name': tag['name'],
                    'post_count': tag['edge_hashtag_to_media']['count']
                },
                image=tag['profile_pic_url'])

        #  Если есть следующая страница - переходим на нее
        if js_data['graphql']['hashtag']['edge_hashtag_to_media']['page_info']['has_next_page']:
            yield response.follow(f'https://www.instagram.com/explore/tags/{tag["name"]}/?__a=1&max_id={end_cursor}',
                                  callback=self.json_parse)

        # Пробегаем все посты, запихиваем их в item'ы
        for edge in js_data['graphql']['hashtag']['edge_hashtag_to_media']['edges']:
            yield InstagramPost(date_parse=dt.datetime.utcnow(), data=edge['node'], image=edge['node']['display_url'])

        # Вариант с отлавливанием хэшей и подстановкой в запрос
        # def tag_page_parse(self, response):
        #     try:
        #         data = self.script_data(response)
        #         if not self.csrf_token:
        #             self.csrf_token = data['config']['csrf_token']
        #         hash_data = data['entry_data']['TagPage'][0]['graphql']
        #     except Exception:
        #         hash_data = response.json()
        #
        #     variables = {
        #         "tag_name": hash_data['hashtag']['name'],
        #         "first": 50,
        #         "after": hash_data['hashtag']['edge_hashtag_to_media']['page_info']['end_cursor']
        #     }
        #     url = f'{self.graphql_url}?query_hash={self.query["tags"]}&variables={json.dumps(variables)}'
        #     if hash_data['hashtag']['edge_hashtag_to_media']['page_info']['has_next_page']:
        #         yield response.follow(url, callback=tag_page_parse)
