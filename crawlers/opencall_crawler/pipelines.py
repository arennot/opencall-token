import os
import logging
from supabase import create_client, Client
from itemadapter import ItemAdapter

logger = logging.getLogger(__name__)


class SupabasePipeline:
    """将爬取结果写入 Supabase PostgreSQL。"""

    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(url, key)
        self.seen_urls = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # 去重：同一条 URL 不重复入库
        url = adapter.get("url")
        if url and url in self.seen_urls:
            spider.logger.info(f"Skipping duplicate URL: {url}")
            return item
        if url:
            self.seen_urls.add(url)

        # 类型标准化
        raw_type = adapter.get("type", "").strip().lower()
        type_map = {
            "open call": "opencall",
            "call": "opencall",
            "call for entries": "opencall",
            "residency": "residency",
            "residence": "residency",
            "grant": "grant",
            "fellowship": "grant",
            "funding": "grant",
        }
        mapped_type = type_map.get(raw_type, raw_type)
        if mapped_type not in ("opencall", "residency", "grant"):
            mapped_type = "opencall"  # 默认
        adapter["type"] = mapped_type

        # 学科列表清洗
        disciplines = adapter.get("disciplines", [])
        if disciplines and isinstance(disciplines, str):
            disciplines = [d.strip() for d in disciplines.split(",")]
        adapter["disciplines"] = disciplines if disciplines else []

        # 设置默认值
        adapter.setdefault("status", "published")
        adapter.setdefault("is_local", False)
        adapter.setdefault("featured", False)
        adapter.setdefault("disciplines", [])

        # 写入 Supabase
        data = {
            "title": adapter["title"],
            "type": adapter["type"],
            "organization": adapter["organization"],
            "deadline": adapter.get("deadline") or None,
            "location": adapter.get("location") or None,
            "disciplines": adapter["disciplines"],
            "funding": adapter.get("funding") or None,
            "description": adapter.get("description") or None,
            "url": url or None,
            "source": adapter.get("source", spider.name),
            "posted_at": adapter.get("posted_at") or None,
            "featured": adapter["featured"],
            "is_local": adapter["is_local"],
            "status": adapter["status"],
        }

        try:
            # 先查是否已存在（基于 url 去重）
            if url:
                existing = self.supabase.table("opportunities").select("id").eq("url", url).execute()
                if existing.data and len(existing.data) > 0:
                    spider.logger.info(f"Already exists in DB: {url}")
                    return item

            result = self.supabase.table("opportunities").insert(data).execute()
            spider.logger.info(f"Inserted: {adapter['title']} ({adapter['type']})")
        except Exception as e:
            spider.logger.error(f"Failed to insert {adapter['title']}: {e}")

        return item
