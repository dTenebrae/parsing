import scrapy
from urllib.parse import urljoin
from ..loaders import HeadHuntersLoader
from ..items import HeadHuntersJobItem, HeadHunterCompanyItem


class HeadhuntersSpider(scrapy.Spider):
    name = 'headhunters'
    allowed_domains = ['hh.ru']
    start_urls = ['https://hh.ru/search/vacancy?schedule=remote&L_profession_id=0&area=1']
    xpath_query = {
        'job_url': '//div[contains(@class, "vacancy-serp-item__row")]//a[contains(@data-qa, '
                   '"vacancy-serp__vacancy-title")]/@href',
        'page': '//span[@class="bloko-button-group"]//a[@class="bloko-button HH-Pager-Control"]/@href',
        'job_title': '//h1[@class="bloko-header-1"]//text()',
        'salary': '//p[@class="vacancy-salary"]//text()',
        'description': '//div[@data-qa="vacancy-description"]//text()',
        'tags': '//div[@class="bloko-tag-list"]//text()',
        'employer_url': '//div[@class="vacancy-company-name-wrapper"]//@href',
        'company_name_1': '//h3[@class="b-subtitle b-employerpage-vacancies-title"]/text()',
        'company_name_2': '//span[@class="company-header-title-name"]/text()',
        'company_url': '//a[@class="g-user-content"]/@href',
        'company_desc': '//div[@class="g-user-content"]//text()',
        'other_links': '//a[@data-qa="employer-page__employer-vacancies-link"]/@href',
        'company_fields': '//div[@class="employer-sidebar-block"]/p/text()',
    }

    def parse(self, response, **kwargs):
        for page in response.xpath(self.xpath_query['page']):
            yield response.follow(page, callback=self.parse)

        for job_url in response.xpath(self.xpath_query['job_url']):
            yield response.follow(job_url, callback=self.job_parse)

    def job_parse(self, response):
        loader = HeadHuntersLoader(item=HeadHuntersJobItem(), response=response)
        employer_url = urljoin(response.url, response.xpath(self.xpath_query['employer_url']).extract_first())
        loader.add_xpath('job_title', self.xpath_query['job_title'])
        loader.add_xpath('salary', self.xpath_query['salary'])
        loader.add_xpath('description', self.xpath_query['description'])
        loader.add_xpath('tags', self.xpath_query['tags'])
        loader.add_value('employer_url', employer_url)

        if employer_url:
            yield response.follow(employer_url, callback=self.employer_parse)

        yield loader.load_item()

    def employer_parse(self, response):
        loader = HeadHuntersLoader(item=HeadHunterCompanyItem(), response=response)
        _a = response.xpath(self.xpath_query['company_name_1']).get()
        company_name = _a[_a.find('«') + 1: _a.find('»')] if _a else ''.join(
            response.xpath(self.xpath_query['company_name_2']).getall()[:2]),
        loader.add_value('company_name', company_name)
        loader.add_xpath('company_url', self.xpath_query['company_url'])
        loader.add_xpath('company_desc', self.xpath_query['company_desc'])
        loader.add_xpath('company_fields', self.xpath_query['company_fields'])

        other_links = response.xpath(self.xpath_query['other_links']).get()
        if other_links:
            yield response.follow(other_links, callback=self.parse)

        yield loader.load_item()
