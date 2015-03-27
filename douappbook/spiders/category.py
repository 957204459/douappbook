# -*- coding: utf-8 -*-
try:
    import simplejson as json
except ImportError:
    import json

import furl
from scrapy import Request

from douappbook.spiders import DoubanAppSpider
from douappbook.items import BookItem, RatingItem


class CategorySpider(DoubanAppSpider):
    name = "category"
    allowed_domains = ["douban.com"]

    def start_requests(self):
        url = self.get_api_url(
            'tag/3/categories',
            start=0,
            count=20,
            editor_choice=0
        )
        yield Request(url, callback=self.parse)

    def parse(self, response):
        res = json.loads(response.body_as_unicode())
        categories = res['categories']
        for cat in categories:
            cat_id = cat['id']
            for tp in ('latest', 'score', 'hot'):
                endpoint = 'subject_collection/%s_%s/subjects' % (cat_id, tp)
                url = self.get_api_url(
                    endpoint,
                    start=0,
                    count=20
                )
                yield Request(url, callback=self.parse_subjects)
                if self.settings['DEBUG']:
                    break
            if self.settings['DEBUG']:
                break

    def parse_subjects(self, response):
        res = json.loads(response.body_as_unicode())
        start = res['start']
        count = res['count']
        total = res['total']
        subjects = res['subjects']
        for sub in subjects:
            if not sub['author']:
                continue
            book = BookItem()
            book['id'] = int(sub['id'])
            book['title'] = sub['title']
            book['author'] = sub['author'][0]
            book['url'] = sub['url']
            book['cover'] = sub['pic']['normal']
            book['rating'] = sub['rating']['value']
            book['rating_count'] = sub['rating']['count']
            yield book

            endpoint = 'book/%d/interests' % book['id']
            rating_url = self.get_api_url(
                endpoint,
                start=0,
                count=20
            )
            yield Request(rating_url, callback=self.parse_rating)
            if self.settings['DEBUG']:
                break

        if start + count < total and not self.settings['DEBUG']:
            _url = furl.furl(response.url)
            _url.args['start'] = start + count
            url = _url.url
            yield Request(url, callback=self.parse)

    def parse_rating(self, response):
        api_url = furl.furl(response.url)
        book_id = int(api_url.path.segments[3])

        res = json.loads(response.body_as_unicode())
        start = res['start']
        count = res['count']
        total = res['total']
        interests = res['interests']
        for item in interests:
            rating = RatingItem()
            rating['id'] = item['id']
            rating['book_id'] = book_id
            rating['user_id'] = item['user']['id']
            rating['username'] = item['user']['uid']
            rating['rating'] = item['rating']['value']
            rating['vote'] = item['vote_count']
            rating['comment'] = item['comment']
            yield rating

        if start + count < total and not self.settings['DEBUG']:
            endpoint = 'book/%d/interests' % book_id
            url = self.get_api_url(
                endpoint,
                start=start + count,
                count=20
            )
            yield Request(url, callback=self.parse_rating)