import scrapy

class OpportunityItem(scrapy.Item):
    title = scrapy.Field()
    type = scrapy.Field()
    organization = scrapy.Field()
    deadline = scrapy.Field()
    location = scrapy.Field()
    disciplines = scrapy.Field()
    funding = scrapy.Field()
    description = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
    posted_at = scrapy.Field()
    featured = scrapy.Field()
    is_local = scrapy.Field()
    status = scrapy.Field()
