import scrapy
import re
from dateparser import parse as parse_date
from ..items import OpportunityItem


class TransartistsSpider(scrapy.Spider):
    """爬取 Transartists 驻留与机会列表 (2026-07 新版 HTML 结构)"""

    name = "transartists"
    allowed_domains = ["transartists.org"]
    start_urls = ["https://www.transartists.org/en/transartists-calls"]

    def parse(self, response):
        """解析列表页 -- 新版 table 结构"""
        for row in response.css("table.table.cols-0 tr"):
            link = row.css("td.views-field-view-node h2 a::attr(href)").get()
            if link:
                yield response.follow(link, callback=self.parse_detail)

        # 翻页
        next_link = response.css("li.pager__item--next a.page-link::attr(href)").get()
        if next_link:
            yield response.follow(next_link, callback=self.parse)

    def parse_detail(self, response):
        item = OpportunityItem()

        # -- 标题 --
        item["title"] = response.css(".page-title span::text").get("").strip()
        if not item["title"]:
            item["title"] = response.css("h1::text").get("").strip()

        # -- 来源 & URL --
        item["source"] = "transartists"
        item["url"] = response.url

        # -- 组织/机构 --
        org_raw = response.css(".field--name-field-authors .field__item::text").get("")
        org = org_raw.strip()
        if org.lower().startswith("courtesy of "):
            org = org[12:].strip()
        item["organization"] = org or "Transartists"

        # -- 类型推断（从标题提取）--
        title_lower = item["title"].lower()
        if ("residency" in title_lower or "residence" in title_lower
                or "residencies" in title_lower or "residential" in title_lower):
            item["type"] = "residency"
        elif "grant" in title_lower or "funding" in title_lower or "fellowship" in title_lower:
            item["type"] = "grant"
        else:
            item["type"] = "opencall"

        # -- 正文提取 --
        body_elements = response.css(
            ".paragraph--type--text .field--name-field-paragraph-body *::text"
        ).getall()
        body_text = " ".join(body_elements).strip()

        # -- 截止日期（从正文正则提取）--
        patterns = [
            r"deadline[\s:]+([A-Z][a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})",
            r"deadline[\s:]+(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})",
            r"closes[\s:]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
            r"deadline[\s:]+(\w+\s+\d{1,2},?\s+\d{4})",
            r"Applications?[\s:]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
            r"apply[\s:]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                dt = parse_date(
                    match.group(0).split(":")[-1].strip()
                    if ":" in match.group(0) else match.group(1)
                )
                if dt:
                    item["deadline"] = dt.strftime("%Y-%m-%d")
                    break

        # -- 地点（从正文正则提取）--
        loc_match = re.search(
            r"Location:\s*(.+?)(?:\s\u2022|\.\s|\n|$)",
            body_text, re.IGNORECASE
        )
        if loc_match:
            item["location"] = loc_match.group(1).strip()
        else:
            item["location"] = None


        # -- 资金（从正文正则提取）--
        funding_patterns = [
            r"(?:stipend|budget|honorarium|compensation|grant|fee)[\s:]+[\u20ac$\u00a3]\s*[\d,.-]+",
            r"(?:stipend|budget|honorarium|compensation|grant|fee)[\s:]+[^.]*\d{3,}",
            r"(?:funding|includes|offers?)[^.]*[\u20ac$\u00a3]\s*[\d,.-]+[^.]*\.",
        ]
        for fp in funding_patterns:
            fm = re.search(fp, body_text, re.IGNORECASE)
            if fm:
                item["funding"] = fm.group(0).strip()
                break

        # -- 介绍/描述 --
        intro = response.css(
            ".field--name-field-introduction .field__item::text"
        ).get("").strip()
        if intro:
            item["description"] = intro[:500]
        else:
            paras = response.css(
                ".paragraph--type--text .field--name-field-paragraph-body > p::text"
            ).getall()
            combined = " ".join(p.strip() for p in paras if p.strip())[:500]
            item["description"] = combined

        # -- 学科（从标题和正文关键词推断）--
        discipline_keywords = {
            "visual arts": "\u89c6\u89c9\u827a\u672f", "visual art": "\u89c6\u89c9\u827a\u672f",
            "painting": "\u7ed8\u753b", "sculpture": "\u96d5\u5851", "photography": "\u6444\u5f71",
            "digital art": "\u6570\u5b57\u827a\u672f", "new media": "\u65b0\u5a92\u4f53",
            "installation": "\u88c5\u7f6e", "performance": "\u8868\u6f14",
            "music": "\u97f3\u4e50", "sound": "\u58f0\u97f3",
            "film": "\u7535\u5f71", "video": "\u5f71\u50cf",
            "writing": "\u5199\u4f5c", "literature": "\u6587\u5b66",
            "dance": "\u821e\u8e48", "theatre": "\u620f\u5267", "theater": "\u620f\u5267",
            "architecture": "\u5efa\u7b51", "design": "\u8bbe\u8ba1",
            "printmaking": "\u7248\u753b", "ceramics": "\u9676\u74f7",
            "multimedia": "\u8de8\u5a92\u4ecb", "interdisciplinary": "\u8de8\u5b66\u79d1",
            "cross-disciplinary": "\u8de8\u5b66\u79d1",
        }
        found = set()
        text_to_scan = (title_lower + " " + body_text[:2000]).lower()
        for eng, cn in discipline_keywords.items():
            if eng in text_to_scan:
                found.add(cn)
        item["disciplines"] = sorted(found) if found else []

        # -- 发布日期 --
        posted_raw = response.css(
            ".field--name-field-date-of-publication time::attr(datetime)"
        ).get("")
        if posted_raw:
            dt = parse_date(posted_raw)
            if dt:
                item["posted_at"] = dt.strftime("%Y-%m-%d")

        item["featured"] = False
        yield item