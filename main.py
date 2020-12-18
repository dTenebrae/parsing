# pip install -r requirements.txt
import os
import sys
import dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from gb_parse import settings
from gb_parse.spiders.instagram import InstagramSpider


def main(start_usr='dtenebrae',
         end_usr='gizmothenudist',
         log_level=''):
    # Создаем объект - обработчик файла настроек
    crawl_settings = Settings()
    # Пихаем наш файл настроек в него
    crawl_settings.setmodule(settings)
    # Создаем процесс управляющий пауками
    crawl_proc = CrawlerProcess(settings=crawl_settings)
    # Передаем класс нашего паука (процесс сам его создаст)
    crawl_proc.crawl(InstagramSpider,
                     start_user=start_usr,
                     end_user=end_usr,
                     login=os.getenv('MAIN_USER_INST_LOGIN'),
                     password=os.getenv('MAIN_USER_INST_PASS'),
                     log_level=log_level)
    # Собственно, стартуем
    crawl_proc.start()


if __name__ == '__main__':
    dotenv.load_dotenv('.env')
    arg_len = len(sys.argv)
    if arg_len == 1:
        main()
    elif sys.argv[1] == '--help' or sys.argv[1] == '-h':
        print('Usage: main.py [OPTION] start_user end_user\n'
              'Find a connection between 2 users in Instagram. If no arguments received - using default users.'
              '\nPossible arguments:'
              '\n -h, --help   Showing this short manual'
              '\n -l, --log    This option enables logging in form of tree-like relations between users')
        sys.exit(0)
    elif (arg_len == 2) and (sys.argv[1] == '--log' or sys.argv[1] == '-l'):
        main(log_level=sys.argv[1])
        sys.exit(0)
    elif (arg_len == 3) and (sys.argv[1] == '--log' or sys.argv[1] == '-l'):
        print("Incorrect arguments. Use '--help' or '-h' for help")
    elif (arg_len == 4) and (sys.argv[1] == '--log' or sys.argv[1] == '-l'):
        main(start_usr=sys.argv[2], end_usr=sys.argv[3], log_level=sys.argv[1])
        sys.exit(0)
    elif (arg_len == 2) or (arg_len > 3):
        print("Incorrect arguments. Use '--help' or '-h' for help")
        sys.exit(1)
    else:
        main(start_usr=sys.argv[1], end_usr=sys.argv[2])

