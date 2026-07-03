#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高德地图 POI 批量抓取脚本 —— 北京艺术场馆数据采集

功能说明：
  利用高德地图 Web 服务 API（text_search 接口），批量检索北京
  美术馆、当代艺术中心、艺术空间、画院、画廊等关键词，经过两阶段
  清洗（分类路由 -> 缓冲池噪音过滤 + 关键字打捞），输出结构化的
  场馆 CSV 数据，用于艺术聚合平台。

两阶段流程：
  第一阶段：分页检索 + 分类路由
    - 140400（美术馆）-> 直接收录
    - 140200/140000/140100/170000/170100/170200/110204/061300/061301 -> 缓冲池
    - 其余 -> 丢弃
  第二阶段：缓冲池清洗
    - 黑名单噪音过滤
    - 关键字打捞（名/类/址需含艺术、美术、画院、美术馆、画廊、空间、中心、馆等）

使用方法（GitHub Actions）：
  通过环境变量 AMAP_KEY 传入高德 Web 服务 API Key。
  本地运行时：$env:AMAP_KEY="your_key"; python fetch_art_venues.py

依赖：
  pip install pandas requests
"""

import time
import requests
import pandas as pd
import os

# ============================================================
# 1. 参数配置（入口配置区）
# ============================================================

# 高德地图 Web 服务 API Key（从环境变量读取，适配 GitHub Actions）
AMAP_KEY = os.environ.get("AMAP_KEY", "")

# 高德 POI 搜索接口地址
AMAP_TEXT_SEARCH_URL = "https://restapi.amap.com/v3/place/text"

# 目标城市
CITY = "北京市"

# 检索关键字列表
KEYWORDS = [
    "美术馆", "当代艺术", "艺术空间", "画院",
    "画廊", "艺术中心", "空间", "gallery",
]

# 噪音黑名单 —— 凡是名称、类型或地址命中以下任一词条，直接丢弃
NOISE_KEYWORDS = [
    "培训", "儿童", "少儿", "画室", "教育", "班",
    "刺青", "纹身", "婚纱", "摄影", "设计", "家居",
    "快印", "家具", "建材", "餐厅", "咖啡",
    # === 茶空间与休闲娱乐黑名单 ===
    "茶空间", "茶艺", "茶道", "茶楼", "茶馆", "禅茶", "围炉煮茶",
]

# 关键字打捞词 —— 对缓冲池数据做二次筛选，名/类/址中含以下词则保留
SALVAGE_KEYWORDS = [
    "艺术", "美术", "画院", "美术馆", "画廊",
    "空间", "中心", "馆",
    "gallery", "space",
]

# 直接收录分类编码（此类 POI 一步到位，不经过任何清洗）
DIRECT_TYPECODES = {
    "140400",  # 美术馆
}

# 缓冲池分类编码（此类 POI 先收入缓冲池，再统一做噪音过滤 + 关键字打捞）
BUFFER_TYPECODES = {
    "140200",  # 展览馆
    "140000",  # 科教文化场所
    "140100",  # 博物馆
    "170000",  # 公司企业
    "170100",  # 知名企业
    "170200",  # 公司
    "110204",  # 纪念馆
    "061300",  # 特殊买卖场所
    "061301",  # 拍卖行
}

# 高德 API 单页最大返回条数（官方上限 25）
PAGE_SIZE = 25

# 请求间隔（秒），用于避免触发 QPS 限制
REQUEST_INTERVAL = 0.5

# 输出文件名
OUTPUT_CSV = "beijing_art_museums_raw.csv"


# ============================================================
# 2. 核心处理函数
# ============================================================

def is_noise(poi: dict) -> bool:
    """判断 POI 是否为噪音：检查 name / type / address 三字段，
    若包含 NOISE_KEYWORDS 中任一关键词则返回 True（应丢弃）。"""
    name = str(poi.get("name", ""))
    ptype = str(poi.get("type", ""))
    address = str(poi.get("address", ""))
    for kw in NOISE_KEYWORDS:
        if kw in name or kw in ptype or kw in address:
            return True
    return False


def has_salvage_keyword(poi: dict) -> bool:
    """关键字打捞：检查 POI 的 name / type / address 三字段中
    是否包含 SALVAGE_KEYWORDS 中的任意一个词。命中则保留。"""
    name = str(poi.get("name", ""))
    ptype = str(poi.get("type", ""))
    address = str(poi.get("address", ""))
    for kw in SALVAGE_KEYWORDS:
        if kw.lower() in name.lower() or kw.lower() in ptype.lower() or kw.lower() in address.lower():
            return True
    return False


def classify_poi(poi: dict) -> str:
    """根据 typecode 对 POI 分类路由。
    返回值："direct"（直接收录）| "buffer"（进入缓冲池）| "discard"（丢弃）"""
    typecode = poi.get("typecode", "")
    if typecode in DIRECT_TYPECODES:
        return "direct"
    if typecode in BUFFER_TYPECODES:
        return "buffer"
    return "discard"


def extract_fields(poi: dict) -> dict:
    """从高德 API 返回的单条 POI 字典中提取所需字段。"""
    return {
        "id": poi.get("id", ""),
        "name": poi.get("name", ""),
        "type": poi.get("type", ""),
        "typecode": poi.get("typecode", ""),
        "pname": poi.get("pname", ""),
        "cityname": poi.get("cityname", ""),
        "adname": poi.get("adname", ""),
        "address": poi.get("address", ""),
        "location": poi.get("location", ""),
        "tel": poi.get("tel", ""),
    }


def clean_buffer(buffer: list[dict]) -> list[dict]:
    """缓冲池清洗：先过滤噪音，再关键字打捞，通过者收录。"""
    result = []
    noise_count = 0
    for poi in buffer:
        if is_noise(poi):
            noise_count += 1
            continue
        if has_salvage_keyword(poi):
            result.append(extract_fields(poi))
    print(f"  缓冲池清洗：{len(buffer)} 条 -> 噪音过滤移除 {noise_count} 条 -> "
          f"打捞后收录 {len(result)} 条")
    return result


# ============================================================
# 3. 分页检索与两阶段采集
# ============================================================

def fetch_all_venues() -> list[dict]:
    """
    两阶段采集流程：
    第一阶段 —— 分页检索与分类路由：
      遍历每个关键字，逐页请求高德 POI 搜索 API。
      对每条 POI 根据 typecode 路由：
        - "direct" -> 直接收录到最终列表
        - "buffer" -> 暂存到缓冲池
        - "discard" -> 直接丢弃
      全局以 id 去重。
    第二阶段 —— 缓冲池清洗与打捞：
      噪音过滤 -> 关键字打捞 -> 收录。
    """
    seen_ids: set[str] = set()
    all_venues: list[dict] = []
    buffer_pool: list[dict] = []

    for keyword in KEYWORDS:
        print(f"\n====== 开始检索关键词：{keyword} ======")
        page = 1

        while True:
            params = {
                "key": AMAP_KEY,
                "keywords": keyword,
                "city": CITY,
                "offset": PAGE_SIZE,
                "page": page,
                "extensions": "all",
                "output": "JSON",
            }

            try:
                resp = requests.get(AMAP_TEXT_SEARCH_URL, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except requests.exceptions.RequestException as e:
                print(f"  [错误] 网络请求失败（第{page}页）：{e}")
                break
            except ValueError as e:
                print(f"  [错误] JSON 解析失败（第{page}页）：{e}")
                break

            status = data.get("status", "0")
            if status != "1":
                info = data.get("info", "未知错误")
                print(f"  [错误] API 返回异常（第{page}页）：{info}")
                if data.get("infocode") == "10003":
                    print("  [严重] API 额度超限，终止抓取。")
                    all_venues.extend(clean_buffer(buffer_pool))
                    return all_venues
                break

            pois = data.get("pois", [])
            total_count = int(data.get("count", 0))

            if not pois:
                print(f"  第{page}页无数据，结束当前关键词。")
                break

            page_direct = 0
            page_buffer = 0

            for poi in pois:
                poi_id = poi.get("id", "")
                if poi_id in seen_ids:
                    continue
                seen_ids.add(poi_id)

                route = classify_poi(poi)
                if route == "discard":
                    continue
                if route == "direct":
                    all_venues.append(extract_fields(poi))
                    page_direct += 1
                elif route == "buffer":
                    buffer_pool.append(poi)
                    page_buffer += 1

            print(f"  第{page}页：共 {len(pois)} 条 | "
                  f"直接收录 {page_direct} | 缓冲池 {page_buffer} | "
                  f"累计直接收录 {len(all_venues)} | 缓冲池累计 {len(buffer_pool)}")

            if len(pois) < PAGE_SIZE or page * PAGE_SIZE >= total_count:
                print(f"  已翻至最后一页，结束关键词「{keyword}」。")
                break

            page += 1
            time.sleep(REQUEST_INTERVAL)

    # === 第二阶段：缓冲池清洗与打捞 ===
    print(f"\n====== 缓冲池清洗与关键字打捞 ======")
    print(f"  缓冲池初始记录数：{len(buffer_pool)}")

    cleaned = clean_buffer(buffer_pool)
    all_venues.extend(cleaned)

    return all_venues


# ============================================================
# 4. 主流程
# ============================================================

def main():
    print("=" * 60)
    print("高德地图 POI 抓取工具 —— 北京艺术场馆数据采集")
    print("=" * 60)
    print(f"检索关键词：{KEYWORDS}")
    print(f"噪音黑名单：{NOISE_KEYWORDS}")
    print(f"打捞关键词：{SALVAGE_KEYWORDS}")
    print(f"目标城市：{CITY}")
    print(f"直接收录 typecode：{DIRECT_TYPECODES}")
    print(f"缓冲池 typecode：{BUFFER_TYPECODES}")
    print(f"输出文件：{OUTPUT_CSV}")
    print("=" * 60)

    if not AMAP_KEY:
        print("\n[错误] 环境变量 AMAP_KEY 未设置。")
        print("请在 GitHub Actions 的 repo secrets 中添加 AMAP_KEY")
        print("或本地运行：$env:AMAP_KEY=\"your_key\"; python fetch_art_venues.py")
        return

    venues = fetch_all_venues()

    if not venues:
        print("\n未获取到任何有效数据，请检查 API Key 或网络连接。")
        return

    # 转为 DataFrame
    df = pd.DataFrame(venues)

    # 按行政区 + 场馆名称排序
    df = df.sort_values(["adname", "name"]).reset_index(drop=True)

    # 导出 CSV（utf-8-sig 确保 Excel 打开不乱码）
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"\n{'=' * 60}")
    print(f"抓取完成！最终收录 {len(df)} 个场馆。")
    print(f"数据已保存至：{OUTPUT_CSV}")
    print(f"{'=' * 60}")

    # 简要统计
    print("\n=== 各区场馆数量统计 ===")
    area_stats = df["adname"].value_counts().sort_index()
    for area, count in area_stats.items():
        print(f"  {area}：{count} 家")

    # typecode 分布
    print("\n=== typecode 分类统计 ===")
    type_stats = df["typecode"].value_counts().sort_index()
    for tc, count in type_stats.items():
        print(f"  {tc}：{count} 家")


if __name__ == "__main__":
    main()
