import scrapy
import json
import datetime as dt
from gb_parse.items import InstagramUser


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    allowed_domains = ['www.instagram.com']
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    graphql_url = '/graphql/query/'
    start_urls = ['https://www.instagram.com/']
    csrf_token = ''
    checked_tags = []
    query = {
        # 'posts': '56a7068fea504063273cc2120ffd54f3',
        # 'tags': "9b498c08113f1e09617a1703c22b2f32",
        'edge_followed_by': 'c76146de99bb02f6415203be841dd25a',
        'edge_follow': 'd04b0a864b4b54837c0d870b0e77e076'
    }

    def __init__(self, login, password, start_users: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_users = [f'/{user}/' for user in start_users]
        # self.start_tags = [f'/explore/tags/{tag}/' for tag in start_tags]
        # self.start_tags = [f'/explore/tags/{tag}/?__a=1' for tag in start_tags]
        self.login = login
        self.password = password

    @staticmethod
    def script_data(response) -> dict:
        return json.loads(response.xpath('//script[contains(text(),"window._sharedData")]/text()').get().replace(
            'window._sharedData = ', '').rstrip(';'))

    def get_url(self, user_id, after='', flw='edge_followed_by'):
        variables = {"id": user_id,
                     "include_reel": True,
                     "fetch_mutual": False,  # Показывать общих фолловеров
                     "first": 100,
                     "after": after}
        return f'{self.graphql_url}?query_hash={self.query[flw]}&variables={json.dumps(variables)}'

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
                for user in self.start_users:
                    yield response.follow(user, callback=self.user_parse)

    def user_parse(self, response):
        json_data = self.script_data(response)
        user_id = json_data['entry_data']['ProfilePage'][0]['graphql']['user']['id']
        user_name = json_data['entry_data']['ProfilePage'][0]['graphql']['user']['username']
        # Бежим по хэшам. В мету передаем данные, которые потом используем в сборке итема
        for flw in self.query.keys():
            yield response.follow(self.get_url(user_id, flw=flw), callback=self.follow_parse,
                                  meta={'user_id': user_id, 'user_name': user_name, 'follow': flw})

    def follow_parse(self, response):
        json_data = response.json()
        end_cursor = json_data['data']['user'][response.meta['follow']]['page_info']['end_cursor']
        # Идем по пагинации
        if json_data['data']['user'][response.meta['follow']]['page_info']['has_next_page']:
            yield response.follow(
                self.get_url(user_id=response.meta['user_id'], after=end_cursor, flw=response.meta['follow']),
                callback=self.follow_parse, meta=response.meta)
        # Так как путь для followers и followed_by в структуре json меняется - используем это значение из меты
        for edge in json_data['data']['user'][response.meta['follow']]['edges']:
            yield InstagramUser(date_parse=dt.datetime.utcnow(),
                                data={
                                    'root_user': response.meta['user_name'],
                                    'root_user_id': response.meta['user_id'],
                                    'follow_status': response.meta['follow'],
                                    'node_data': edge['node']
                                },
                                image=edge['node']['profile_pic_url'])
