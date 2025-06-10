import scrapy

class BusinessScraperItem(scrapy.Item):
    name = scrapy.Field()
    phone = scrapy.Field()
    address = scrapy.Field()
    locality = scrapy.Field()
    category = scrapy.Field() 