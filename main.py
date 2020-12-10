import os
import dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from gb_parse import settings
# from gb_parse.spiders.autoyoula import AutoyoulaSpider
# from gb_parse.spiders.headhunters import HeadhuntersSpider
from gb_parse.spiders.instagram import InstagramSpider

if __name__ == '__main__':
    # TODO Вынести в данные под конкретного паука
    dotenv.load_dotenv('.env')
    hash_tags = ['python', 'datascience', 'machinelearning', 'deeplearning']

    # Создаем объект - обработчик файла настроек
    crawl_settings = Settings()
    # Пихаем наш файл настроек в него
    crawl_settings.setmodule(settings)
    # Создаем процесс управляющий пауками
    crawl_proc = CrawlerProcess(settings=crawl_settings)
    # Передаем класс нашего паука (процесс сам его создаст)
    crawl_proc.crawl(InstagramSpider,
                     start_tags=hash_tags,
                     login=os.getenv('INST_LOGIN'),
                     password=os.getenv('INST_PASS'))
    # Собственно, стартуем
    crawl_proc.start()
