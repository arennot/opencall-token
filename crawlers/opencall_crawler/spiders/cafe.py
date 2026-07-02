import scrapy
from dateparser import parse as parse_date
from ..items import OpportunityItem


class CafeSpider(scrapy.Spider):
    """爬取 CaFE (CallForEntry) 公开征集列表

    注意：CaFE 页面大量使用 JavaScript 渲染，如果需要完整渲染，
    建议使用 scrapy-playwright 中间件。此版本先做基础 HTML 解析。
    """

    name = "cafe"
    allowed_domains = ["callforentry.org", "cafeapply.com"]
    start_urls = ["https://www.callforentry.org/opportunities/"]

    def parse(self, response):
        """解析机会列表"""
        for item in response.css(".opportunity-item, .cafe-opportunity, .card-opportunity, tr.opportunity"):
            link = item.css("a::attr(href)").get()
            if link and not link.startswith("#"):
                yield response.follow(link, callback=self.parse_detail)

        # 翻页
        next_link = response.css("a.next::attr(href), .pagination a::attr(href), a[rel='next']::attr(href)")
        if next_link:
            yield response.follow(next_link[0], callback=self.parse)

    def parse_detail(self, response):
        item = OpportunityItem()

        item["title"] = response.css("h1::text, .page-title::text, .opportunity-title::text").get("").strip()
        item["organization"] = (
            response.css(".field--name-field-organization .field__item::text").get("").strip()
            or response.css(".organization-name::text").get("").strip()
            or "CaFE"
        )
        item["source"] = "cafe"
        item["url"] = response.url

        # 类型：CaFE 主要是公开征集
        type_text = " ".join(response.css(".field--name-field-type .field__item::text, .opportunity-type::text").getall()).lower()
        if "residency" in type_text:
            item["type"] = "residency"
        elif "grant" in type_text or "fellowship" in type_text:
            item["type"] = "grant"
        else:
            item["type"] = "opencall"

        # 截止日期
        deadline_text = (
            response.css(".field--name-field-deadline .field__item::text").get("")
            or response.css(".deadline-date::text").get("")
        )
        if deadline_text:
            dt = parse_date(deadline_text.strip())
            if dt:
                item["deadline"] = dt.strftime("%Y-%m-%d")

        item["location"] = (
            response.css(".field--name-field-location .field__item::text").get("").strip()
            or response.css(".opportunity-location::text").get("").strip()
            or None
        )

        # 资助
        funding_text = response.css(".field--name-field-funding .field__item::text, .opportunity-funding::text").get("")
        if funding_text:
            item["funding"] = funding_text.strip()

        # 描述
        desc_parts = response.css(".content p::text, .opportunity-description p::text, .field--name-body p::text").getall()
        item["description"] = " ".join(desc_parts).strip()[:500] if desc_parts else None

        # 学科
        disciplines = (
            response.css(".field--name-field-discipline .field__item::text").getall()
            or response.css(".opportunity-disciplines .discipline-tag::text").getall()
        )
        item["disciplines"] = [d.strip() for d in disciplines if d.strip()]

        item["featured"] = False
        yield item
