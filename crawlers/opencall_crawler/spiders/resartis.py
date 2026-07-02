import scrapy
from dateparser import parse as parse_date
from ..items import OpportunityItem


class ResArtisSpider(scrapy.Spider):
    """爬取 Res Artis 驻留项目目录"""

    name = "resartis"
    allowed_domains = ["resartis.org"]
    start_urls = ["https://resartis.org/residencies/"]

    def parse(self, response):
        """解析列表页，提取每个驻留项目的链接"""
        # Res Artis 使用 post 列表布局
        links = response.css("a.post-title::attr(href), .residency-item a::attr(href), article a::attr(href)")
        if not links:
            # 备用选择器
            links = response.css("h2 a::attr(href), h3 a::attr(href)")
        for link in links:
            yield response.follow(link, callback=self.parse_detail)

        # 翻页
        next_page = response.css("a.next::attr(href), .pagination a.next::attr(href), a[rel='next']::attr(href)")
        if next_page:
            yield response.follow(next_page[0], callback=self.parse)

    def parse_detail(self, response):
        """解析详情页"""
        item = OpportunityItem()

        item["title"] = self._extract(response, "h1::text, .entry-title::text, .post-title::text")
        item["organization"] = "Res Artis"
        item["source"] = "resartis"
        item["type"] = "residency"
        item["url"] = response.url

        # 尝试提取各个字段
        body_text = response.css(".entry-content, .post-content, article").getall()
        body_text = " ".join(body_text)

        item["location"] = self._find_between(body_text, ["Location", "Country", "City"])
        item["funding"] = self._find_between(body_text, ["Funding", "Financial", "Grant", "Stipend", "Fee"])
        item["deadline"] = self._parse_deadline(body_text)
        item["disciplines"] = self._find_disciplines(body_text)
        item["description"] = response.css(".entry-content p::text, .post-content p::text").get()

        yield item

    def _extract(self, response, selector):
        el = response.css(selector)
        return el.get("").strip() if el else ""

    def _find_between(self, text, keywords):
        """简单的关键字 + 附近文本提取"""
        for kw in keywords:
            idx = text.lower().find(kw.lower())
            if idx != -1:
                # 提取关键字后的一小段文本
                snippet = text[idx:idx+200]
                # 尝试找到冒号后的内容
                colon = snippet.find(":")
                if colon != -1 and colon < 50:
                    return snippet[colon+1:colon+100].strip().rstrip(",;")
        return None

    def _parse_deadline(self, text):
        """从文本中提取截止日期"""
        import re
        patterns = [
            r"deadline[\s:]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
            r"deadline[\s:]+(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})",
            r"application[\s:]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
            r"closes[\s:]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dt = parse_date(match.group(1))
                if dt:
                    return dt.strftime("%Y-%m-%d")
        return None

    def _find_disciplines(self, text):
        disciplines = [
            "visual arts", "visual art", "painting", "sculpture", "photography",
            "digital media", "new media", "media art", "video", "film",
            "performance", "dance", "theatre", "music", "sound",
            "literature", "writing", "poetry", "ceramics", "printmaking",
            "textile", "fiber art", "installation", "mixed media",
            "architecture", "design", "illustration", "comics",
        ]
        found = []
        text_lower = text.lower()
        for d in disciplines:
            if d in text_lower:
                found.append(d.title())
        return found
