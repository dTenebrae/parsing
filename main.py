from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

from gb_parse import settings
from gb_parse.spiders.autoyoula import AutoyoulaSpider

if __name__ == '__main__':
    # Создаем объект - обработчик файла настроек
    crawl_settings = Settings()
    # Пихаем наш файл настроек в него
    crawl_settings.setmodule(settings)
    # Создаем процесс управляющий пауками
    crawl_proc = CrawlerProcess(settings=crawl_settings)
    # Передаем класс нашего паука (процесс сам его создаст)
    crawl_proc.crawl(AutoyoulaSpider)
    # Собственно, стартуем
    crawl_proc.start()

