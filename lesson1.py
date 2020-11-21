import os
from time import sleep
import json
import requests


class ParserShop:
    def __init__(self, prod_url):
        """
        prod_url: URL товаров, которые потом пойдут в файлы категорий
        """
        self.prod_url = prod_url
        self.params = {
            'records_per_page': 20,
            'categories': ''
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:83.0) Gecko/20100101 Firefox/83.0'
        }

    def parse(self, cat_url, delay=100):
        """
        cat_url: URL категорий товаров. Пока используется исключительно под 5ку.
        delay: Задержка между обращениями к серверу, в миллисекундах. По умолчанию 100мс
        """
        #  счетчики
        completed = 1
        err_counter = 0

        params = self.params
        categories = []

        response: requests.Response = requests.get(cat_url)
        if response.status_code == 200:
            categories = response.json()
        else:
            print(f'Ошибка доступа: {response.status_code}')
            exit(1)

        for cat in categories:
            url = self.prod_url
            cat['products'] = []
            params['categories'] = cat['parent_group_code']

            while url:
                response: requests.Response = requests.get(url, params=params, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    url = data.get('next')
                    for product in data.get('results', []):
                        cat['products'].append(product)
                    sleep(delay / 1000)
                else:
                    print(f'Ошибка доступа к товару: {response.status_code}')
                    err_counter += 1
                    if err_counter > 2:
                        print('Сервер недоступен')
                        exit(1)

            if cat['products']:
                self._save_category(cat)

            # Неcтабильно работает в консоли Pycharm
            print(f'Parsing...: {completed / len(categories) * 100: .1f}%', end='\r', flush=True)
            completed += 1

    @staticmethod
    def _save_category(category: dict):
        if not os.path.exists('categories'):
            os.mkdir('categories')
        current_dir = os.path.join(os.getcwd(), 'categories')
        with open(os.path.join(current_dir, f'{category["parent_group_code"]}.json'), 'w', encoding='UTF-8') as file:
            json.dump(category, file, ensure_ascii=False)


if __name__ == '__main__':
    category_url = 'https://5ka.ru/api/v2/categories/'
    products_url = 'https://5ka.ru/api/v2/special_offers/'
    parser = ParserShop(products_url)
    parser.parse(category_url)
    print('Completed successfully.')
