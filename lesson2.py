# dependencies:
# - pymongo
# - bs4
# - lxml
from datetime import datetime as dt
import re
from time import sleep
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import pymongo as pm


class ConnectionException(Exception):
    pass


class ParseMagnit:

    def __init__(self, start_url):
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:83.0) Gecko/20100101 Firefox/83.0'
        }
        _mongo_url = 'mongodb://localhost:27017'
        _db_name = 'parser'
        _col_name = 'magnit'
        self.start_url = start_url

        #  Инициализируем клиент монго, выбираем базу данных (либо создаем, если не существует)
        #  и создаем коллекцию (опять же, если не существует)
        mongo_client = pm.MongoClient(_mongo_url)
        self.db = mongo_client[_db_name]
        #  Проверка на существование коллекции, чтобы избежать дублирования записей при повторном запуске
        if _col_name in self.db.list_collection_names():
            self.db.drop_collection(_col_name)
        self.collection = self.db[_col_name]

    @staticmethod
    def _get(*args, **kwargs) -> BeautifulSoup:
        while True:
            try:
                response: requests.Response = requests.get(*args, **kwargs)
                if response.status_code != 200:
                    print(response.status_code)
                    raise ConnectionException('CError: Connection failed')
                sleep(0.1)
                return BeautifulSoup(response.text, 'lxml')
            except Exception:
                sleep(0.250)

    def run(self):
        soup = self._get(self.start_url, self._headers)
        for product in self._parse(soup):
            self.collection.insert_one(product)

    @staticmethod
    def _str_to_date(dt_string: str) -> tuple:
        """
        Функция перевода строки вида '01 января 23 февраля' в кортеж из 2х переменных типа datetime
        """
        ru_month = {
            'января': '01',
            'февраля': '02',
            'марта': '03',
            'апреля': '04',
            'мая': '05',
            'июня': '06',
            'июля': '07',
            'августа': '08',
            'сентября': '09',
            'октября': '10',
            'ноября': '11',
            'декабря': '12',
        }
        #  регулярками вытаскиваем число и месяц из строки
        from_to_list = re.findall(r'\d+ \w+', dt_string)
        # Замемяем текстовый месяц на число, чтобы нормально перевести в формат datetime
        start_date, end_date = from_to_list[0].split(), from_to_list[1].split()
        start_date.extend([ru_month[start_date.pop()], dt.now().strftime("%Y")])
        end_date.extend([ru_month[end_date.pop()], dt.now().strftime("%Y")])
        return dt.strptime('-'.join(start_date), '%d-%m-%Y'), dt.strptime('-'.join(end_date), '%d-%m-%Y')

    def _parse(self, soup: BeautifulSoup) -> dict:
        catalog = soup.find('div', attrs={'class': 'сatalogue__main'})
        for link in catalog.findChildren('a'):
            try:
                from_to = self._str_to_date(link.find('div', attrs={'class': 'card-sale__date'}).text)
                #  Ищем текст цен до/после - и переводим в float
                n_p = link.find('div', attrs={'class': 'label__price label__price_new'})
                o_p = link.find('div', attrs={'class': 'label__price label__price_old'})
                try:
                    new_price = float(n_p.find('span', attrs={'class': 'label__price-integer'}).text) + \
                                float(n_p.find('span', attrs={'class': 'label__price-decimal'}).text) / 100
                    old_price = float(o_p.find('span', attrs={'class': 'label__price-integer'}).text) + \
                                float(o_p.find('span', attrs={'class': 'label__price-decimal'}).text) / 100
                except ValueError:
                    #  Когда доходим до пустых товаров - выходим из цикла
                    break

                data = {
                    "url": urljoin(self.start_url, link.attrs.get('href')),
                    "promo_name": link.find('div', attrs={'class': 'card-sale__header'}).text,
                    "product_name": link.find('div', attrs={'class': 'card-sale__title'}).text,
                    "old_price": old_price,
                    "new_price": new_price,
                    "image_url": urljoin(self.start_url, link.find('img').attrs.get('data-src')),
                    "date_from": from_to[0],
                    "date_to": from_to[1],
                }
            except AttributeError:
                #  Если натыкаемся, например, на баннер - идем на следующую итерацию
                continue
            yield data


if __name__ == '__main__':
    START_URL = 'https://magnit.ru/promo/?geo=moskva'
    parser = ParseMagnit(START_URL)
    parser.run()
