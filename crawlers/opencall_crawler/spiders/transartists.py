import scrapy
from dateparser import parse as parse_date
from ..items import OpportunityItem


class TransartistsSpider(scrapy.Spider):
    """爬取 Transartists 驻留与机会列表"""

    name = "transartists"
    allowed_domains = ["transartists.org"]
    start_urls = ["https://www.transartists.org/en/transartists-calls"]

    def parse(self, response):
        """解析列表页"""
        for card in response.css("article.opportunity-card, .views-row, .node--type-opportunity"):
            link = card.css("a::attr(href)").get()
            if link:
                yield response.follow(link, callback=self.parse_detail)

        # 翻页
        next_link = response.css("a[rel='next']::attr(href), .pager-next a::attr(href), .pagination__next a::attr(href)")
        if next_link:
            yield response.follow(next_link[0], callback=self.parse)

    def parse_detail(self, response):
        item = OpportunityItem()

        item["title"] = response.css("h1::text").get("").strip()
        item["organization"] = (
            response.css(".field--name-field-organisation .field__item::text").get("").strip()
            or "Transartists"
        )
        item["source"] = "transartists"
        item["url"] = response.url

        # 判断类型
        type_text = response.css(".field--name-field-type .field__item::text").get("").strip().lower()
        if "residency" in type_text:
            item["type"] = "residency"
        elif "grant" in type_text or "funding" in type_text or "fellowship" in type_text:
            item["type"] = "grant"
        else:
            item["type"] = "opencall"

        # 截止日期
        deadline_text = response.css(".field--name-field-deadline .field__item::text").get("")
        if deadline_text:
            dt = parse_date(deadline_text.strip())
            if dt:
                item["deadline"] = dt.strftime("%Y-%m-%d")
        else:
            # 从正文中找
            body = " ".join(response.css(".content p::text").getall())
            import re
            patterns = [
                r"deadline[\s:]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
                r"deadline[\s:]+(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})",
                r"closes[\s:]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
            ]
            for pattern in patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    dt = parse_date(match.group(1))
                    if dt:
                        item["deadline"] = dt.strftime("%Y-%m-%d")
                        break

        item["location"] = response.css(".field--name-field-country .field__item::text").get("").strip() or None

        # 资助
        funding_text = response.css(".field--name-field-funding .field__item::text").get("")
        if funding_text:
            item["funding"] = funding_text.strip()

        # 描述
        item["description"] = " ".join(response.css(".content p::text").getall()).strip()[:500]

        # 学科
        disciplines = response.css(".field--name-field-discipline .field__item::text").getall()
        item["disciplines"] = [d.strip() for d in disciplines if d.strip()]

        item["featured"] = False
        yield item
