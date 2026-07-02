BOT_NAME = "opencall_crawler"
SPIDER_MODULES = ["opencall_crawler.spiders"]
NEWSPIDER_MODULE = "opencall_crawler.spiders"

# Obey robots.txt
ROBOTSTXT_OBEY = True

# 爬取间隔：避免被源站封
DOWNLOAD_DELAY = 2.0
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# 启用 Supabase 写入管道
ITEM_PIPELINES = {
    "opencall_crawler.pipelines.SupabasePipeline": 300,
}

# HTTP 缓存（避免每次重复下载，方便调试）
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24h
HTTPCACHE_DIR = "httpcache"

# User-Agent 轮换
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

# 日志级别
LOG_LEVEL = "INFO"
