import scrapy
import json
from collections import defaultdict, deque
from anytree import Node, RenderTree
from scrapy.exceptions import CloseSpider


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    allowed_domains = ['www.instagram.com']
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    graphql_url = '/graphql/query/'
    start_urls = ['https://www.instagram.com/']

    # Словарь хэшей для получения url'ов following и followed_by
    query = {
        'edge_followed_by': 'c76146de99bb02f6415203be841dd25a',
        'edge_follow': 'd04b0a864b4b54837c0d870b0e77e076'
    }

    follow_dict = defaultdict(lambda: defaultdict(list))
    tree_dict = {}

    def __init__(self, login, password, start_user, end_user, log_level, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Забираем из main'a юзеров, между которыми нужно найти связь
        self.start_user = start_user
        self.end_user = end_user
        # Создаем дерево и в его корень определяем стартового юзера
        self.tree_dict[self.start_user] = Node(self.start_user)
        # Очередь url'ов, для запросов в порядке удаления от стартового юзера
        self.scan_que = deque()
        # Логин и пароль для авторизации паука
        self.login = login
        self.password = password
        # Уровень логгирования
        self.log_level = log_level

    @staticmethod
    def script_data(response) -> dict:
        try:
            return json.loads(response.xpath('//script[contains(text(),"window._sharedData")]/text()').get().replace(
                'window._sharedData = ', '').rstrip(';'))
        except ValueError:
            raise CloseSpider('Something wrong with JSON')

    def get_url(self, user_id, after='', flw='edge_followed_by') -> str:
        """
        Функция для формирования пути(при скролле юзеров, фактически пагинация) для запросов

        :param user_id: id пользователя инсты
        :param after: значение end_cursor'a. Хэш, нужный инсте чтобы знать, с какого места подгружать юзеров.
        :param flw: Хэш following или followed_by
        :return: Возвращает url для запроса
        """
        variables = {"id": user_id,
                     "include_reel": False,
                     "fetch_mutual": False,  # Показывать общих фолловеров с тем юзером, под которым залогинен паук
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
                yield response.follow(f'/{self.start_user}/', callback=self.user_parse)

    def user_parse(self, response):
        """
        Функция из прилетевшего response'a выдирает json структуру из скрипта, содержащего нужные нам данные.
        Кроме того, в response.meta передаем данные о пользователе, чей json мы парсим

        :param response: Принимаем response для парсинга json'a
        :return: Посылаем json структуру на дальнейшую обработку
        """
        json_data = self.script_data(response)
        try:
            json_user = json_data['entry_data']['ProfilePage'][0]['graphql']['user']
            user_id = json_user['id']
            user_name = json_user['username']
            followed_by_count = json_user['edge_followed_by']['count']
            follow_count = json_user['edge_follow']['count']

            # Бежим по хэшам. В мету передаем данные, которые потом используем для всякого
            for flw in self.query.keys():
                yield response.follow(self.get_url(user_id, flw=flw), callback=self.follow_parse,
                                      meta={'user_id': user_id,
                                            'user_name': user_name,
                                            'follow': flw,
                                            'followed_by_count': followed_by_count,
                                            'follow_count': follow_count,
                                            'parent': response.meta.get('parent')})
        except KeyError:
            raise CloseSpider('Wrong JSON received. Probably bad user for crawling...')

    def follow_parse(self, response):
        """
        Функция принимает response в виде json структуры, парсит всех followers и followed_by пользователя,
        берет пересечение этих множеств. По результирующему множеству делаем обход в порядке FIFO с целью
        нахождения end_user'a. Если нашли пагинацию - идем по ней, через yield на саму себя

        :param response: принимаем response в форме json.
        :return: Через yield посылаем новую ссылку в user_parse
        """
        json_data = response.json()
        end_cursor = json_data['data']['user'][response.meta['follow']]['page_info']['end_cursor']
        next_page = json_data['data']['user'][response.meta['follow']]['page_info']['has_next_page']
        user_name = response.meta["user_name"]

        # Идем по пагинации
        if next_page:
            yield response.follow(
                self.get_url(user_id=response.meta['user_id'], after=end_cursor, flw=response.meta['follow']),
                callback=self.follow_parse, meta=response.meta)

        # Обходим всех пользователей, сортируя их по словарям following и followed_by
        for edge in json_data['data']['user'][response.meta['follow']]['edges']:
            if response.meta['follow'] == 'edge_follow':
                self.follow_dict[user_name]['follows'].append(edge['node']['username'])
            else:
                self.follow_dict[user_name]['followed_by'].append(edge['node']['username'])

        if self.log_level:
            print(f'{user_name}: follows {len(self.follow_dict[user_name]["follows"])} '
                  f'| {response.meta["follow_count"]}, '
                  f'followed_by {len(self.follow_dict[user_name]["followed_by"])} '
                  f'| {response.meta["followed_by_count"]}')

        # По условию, что количество обработаных юзеров following и followed_by равно итоговому - забираем
        # пересечение этих множеств и помещаем их в очередь для дальнейшего обхода.
        # Если мы будем сравнивать множества до этого - получим неполное пересечение.
        if (len(self.follow_dict[user_name]["follows"]) == response.meta['follow_count']) and \
                (len(self.follow_dict[user_name]["followed_by"]) == response.meta['followed_by_count']):
            b_follow = []  # список юзеров, которые и following, и followed_by.
            for user in self.follow_dict[user_name]["followed_by"]:
                if user in self.follow_dict[user_name]["follows"]:
                    b_follow.append(user)
                    # создаем дерево, но с условием, что этого юзера в него еще не помещено
                    if user not in self.tree_dict.keys():
                        self.tree_dict[user] = Node(user, parent=self.tree_dict[user_name])

            if self.log_level:
                print(RenderTree(self.tree_dict[self.start_user]))

            # Помещаем список в очередь
            self.scan_que.extend(b_follow)

            if self.log_level:
                print(f'\nКоличество пользователей в очереди: {len(self.scan_que)}')

            # Если нам повезло и мы нашли end_user'a - пишем об этом в консоль, рисуем красивые связи и убиваем паука
            if self.end_user in b_follow:
                print(f'\nКоличество переходов между пользователями {self.start_user} и {self.end_user}: '
                      f'{self.tree_dict[self.end_user].depth}')
                print('Путь:')
                print(' -> '.join([node.name for node in self.tree_dict[self.end_user].iter_path_reverse()]))
                raise CloseSpider('Connection between users found. Stopping spider')

            try:
                # Берем из очереди юзера. Если очередь пуста - значит произошло чудо, мы проверили всех пользователей
                # инсты и не нашли связей
                user = self.scan_que.popleft()
                yield response.follow(f'/{user}/', callback=self.user_parse,
                                      meta={'parent': user_name})
            except IndexError:
                raise CloseSpider("Que is empty. Can't find connection between users")
