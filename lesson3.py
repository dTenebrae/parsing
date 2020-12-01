from time import sleep
from dateutil.parser import parse as du_parse
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin

from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
import models


class Database:
    def __init__(self, db_lnk):
        engine = create_engine(db_lnk, echo=False)
        models.Base.metadata.create_all(bind=engine)
        self.new_session = sessionmaker(bind=engine)

    @staticmethod
    def __if_exists(session, model, **data):
        # Так как у нас в коментах уникальное поле id - проверяем его. Для остальных - url
        if model == models.Comment:
            db_model = session.query(model).filter(model.id == data['id']).first()
        else:
            db_model = session.query(model).filter(model.url == data['url']).first()
        if not db_model:
            db_model = model(**data)

        return db_model

    def save_model(self, data):
        """
        Слепил кадавра из вариантов 3 и 4 уроков, как их понял. Получилось коряво, поэтому надо переделывать
        """
        session = self.new_session()
        tags = []
        for tag in data['tags']:
            tmp_tag = self.__if_exists(session, models.Tag, **tag)
            tags.append(tmp_tag)

        for com in data['comments']:
            tmp_com = self.__if_exists(session, models.Comment, **com)
            session.add(tmp_com)
            try:
                session.commit()
            except exc.SQLAlchemyError:
                session.rollback()

        tmp_writer = self.__if_exists(session, models.Writer, **data['writer'])
        tmp_post = self.__if_exists(session, models.Post, **data['post'], writer=tmp_writer)
        tmp_post.tags.extend(tags)
        session.add(tmp_post)
        try:
            session.commit()
        except exc.SQLAlchemyError:
            session.rollback()
        finally:
            session.close()


class GbBlogParser:
    def __init__(self, start_url, db: Database):
        self._headers = {
            # 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:83.0) Gecko/20100101 Firefox/83.0'
        }
        self.start_url = start_url
        self._not_visited = set()
        self._visited = set()
        self._post_urls = set()
        self.db = db

    @staticmethod
    def _get(*args, **kwargs) -> BeautifulSoup:
        while True:
            try:
                response: requests.Response = requests.get(*args, **kwargs)
                if response.status_code != requests.codes.ok:
                    print(response.status_code)
                    raise ConnectionError
                sleep(0.1)
                return BeautifulSoup(response.text, 'lxml')
            except ConnectionError as CE:
                print(f'Ошибка соединения {CE}')
                sleep(0.250)

    def run(self):
        self._not_visited.update([self.start_url])
        while self._not_visited:
            current_url = self._not_visited.pop()
            self._visited.update([current_url])
            soup = self._get(current_url, self._headers)
            posts, pagination = self._parse_page(soup)
            self._post_urls.update(posts)
            self._not_visited.update(pagination)
            self._not_visited -= self._visited

        for post in self._post_urls:
            page_data = self._parse_post(self._get(post), post)
            self.save(page_data)

    def _parse_page(self, soup: BeautifulSoup):
        ul_pag = soup.find('ul', attrs={'class': 'gb__pagination'})
        paginations = set(
            urljoin(self.start_url, url.get('href')) for url in ul_pag.find_all('a') if url.attrs.get('href'))
        posts = set(
            urljoin(self.start_url, url.get('href')) for url in soup.find_all('a', attrs={'class': 'post-item__title'}))
        return posts, paginations

    def _parse_post(self, soup: BeautifulSoup, url: str) -> dict:
        data = {
            'post': {
                'url': url,
                'title': soup.find('h1').text,
                'date': du_parse(soup.find('time').attrs.get('datetime')),
                'image': soup.find('img').get('src')
            },
            'writer': {
                'name': soup.find('div', attrs={'class': 'text-lg'}).text,
                'url': urljoin(self.start_url, soup.find('div', attrs={'class': 'row m-t'}).find('a').get('href'))
            },
            'comments': [],
            'tags': []
        }

        # TODO Выделить парсинг комментов в отдельную функцию
        commentable_id = soup.find('div', attrs={'class': 'referrals-social-buttons-small-wrapper'}).get(
            'data-minifiable-id')

        comment_tag = {'commentable_type': 'Post',
                       'commentable_id': commentable_id,
                       'order': 'desc'}
        try:
            comm_resp: requests.Response = requests.get('https://geekbrains.ru/api/v2/comments', comment_tag)
            try:
                comment_json = comm_resp.json()
                if comment_json:
                    for comment in comment_json:
                        # TODO Сделать обход children (через рекурсию). Иначе выдираются комменты только первого уровня.
                        tmp_dict = {'id': int(comment['comment']['id']),
                                    'commentable_id': int(commentable_id),
                                    'parent_id': comment['comment']['parent_id'],
                                    'body': comment['comment']['body'],
                                    'user_name': comment['comment']['user']['full_name'],
                                    'user_id': comment['comment']['user']['id'],
                                    'user_url': comment['comment']['user']['url']}
                        data['comments'].append(tmp_dict)
            except ValueError as value_exc:
                print(f'Exception: {value_exc}')
        except ConnectionError as CE:
            print(f'Ошибка загрузки комментариев {CE}')

        for tag in soup.find_all('a', attrs={'class': "small"}):
            tag_data = {
                'url': urljoin(self.start_url, tag.get('href')),
                'name': tag.text
            }
            data['tags'].append(tag_data)
        return data

    def save(self, page_data: dict):
        self.db.save_model(page_data)


if __name__ == '__main__':
    db = Database('sqlite:///gb_blog.db')
    parser = GbBlogParser('https://geekbrains.ru/posts', db)
    parser.run()
