#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高德地图 POI 批量抓取脚本 —— 北京艺术场馆数据采集

功能说明：
  利用高德地图 Web 服务 API（text_search 接口），批量检索北京的美术馆、
  当代艺术中心、艺术空间、画院等关键词，经过噪音过滤与去重后，
  输出结构化的场馆 CSV 数据。

使用方法：
  1. 将下方 AMAP_KEY 替换为你的高德 Web 服务 API Key。
  2. 运行本脚本，等待抓取完成即可在同目录下生成 CSV。

依赖：
  pip install pandas requests
"""

import time
import requests
import pandas as pd
import os

# ============================================================
# 1. 参数配置
# ============================================================

# 高德地图 Web 服务 API Key
AMAP_KEY = os.environ.get("AMAP_KEY", "")


# 高德 POI 搜索接口地址
AMAP_TEXT_SEARCH_URL = "https://restapi.amap.com/v3/place/text"

# 目标城市
CITY = "北京市"

# 检索关键字列表
KEYWORDS = ["美术馆", "当代艺术", "艺术空间", "画院", "画廊", "艺术中心", "空间"]

# 噪音过滤器 —— 凡是名称、类型或地址中包含以下任一词条的 POI 都会被丢弃
NOISE_KEYWORDS = [
    "培训", "儿童", "少儿", "画室", "教育", "班",
    "刺青", "纹身", "婚纱", "摄影", "工作室", "设计",
    "快印", "家具", "建材", "餐厅", "咖啡",
# === 新增茶空间与休闲娱乐黑名单 ===
    "茶空间", "茶艺", "茶道", "茶楼", "茶馆", "禅茶", "围炉煮茶"
]

# 高德 API 单页最大返回条数（官方上限 25，设为 25 以减少请求次数）
PAGE_SIZE = 25

# 请求间隔（秒），用于避免触发 QPS 限制
REQUEST_INTERVAL = 0.3

# 输出文件名
OUTPUT_CSV = "beijing_art_museums_raw.csv"


# ============================================================
# 2. 核心清洗函数
# ============================================================

def is_noise(poi: dict) -> bool:
    """
    判断一条 POI 是否为噪音数据。

    检查 name / type / address 三个字段是否包含 NOISE_KEYWORDS
    中的任意一个词。命中则返回 True（应丢弃）。
    """
    name = poi.get("name", "")
    ptype = poi.get("type", "")
    address = poi.get("address", "")

    for kw in NOISE_KEYWORDS:
        if kw in name or kw in ptype or kw in address:
            return True
    return False


def should_keep_by_type(poi: dict) -> bool:
    """
    根据高德分类编码（typecode）二次筛选，尽可能保留艺术类场馆，
    剔除纯商业零售店铺。

    保留规则（按优先级）：
      1. typecode 以 "16" 开头 —— 高德分类中文化/艺术/体育大类
         （160000 = 文化场馆类，160100 = 博物馆/美术馆等）
      2. typecode 以 "05" 开头 —— 高德分类中风景名胜/旅游景区类
         部分艺术园区可能归为此类
      3. 名称中包含明确的 "艺术空间" —— 即使归类到其他门类
         也很有可能是独立艺术空间

    其余 typecode（如 06 餐饮、07 购物、08 生活服务等）直接丢弃。
    """
    typecode = poi.get("typecode", "")
    name = poi.get("name", "")

    # 文化 / 艺术 / 体育大类
    if typecode.startswith("16"):
        return True
    # 风景名胜 / 旅游景区
    if typecode.startswith("05"):
        return True
    # 名称中带"艺术空间"的白名单
    if "艺术空间" in name or "画廊" in name or "Gallery" in name.into_upper():
        return True

    return False


def extract_fields(poi: dict) -> dict:
    """
    从高德返回的单条 POI 字典中提取所需字段。
    """
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


# ============================================================
# 3. 分页检索与去重逻辑
# ============================================================

def fetch_all_venues() -> list[dict]:
    """
    遍历所有关键字，对每个关键字进行分页拉取，
    经过噪音过滤、类别筛选、全局去重后返回纯净的场馆列表。
    """
    seen_ids: set[str] = set()
    all_venues: list[dict] = []

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

            # 检查 API 返回状态
            status = data.get("status", "0")
            if status != "1":
                info = data.get("info", "未知错误")
                print(f"  [错误] API 返回异常（第{page}页）：{info}")
                # 如果因为额度超限（10003），直接终止整个流程
                if data.get("infocode") == "10003":
                    print("  [严重] API 额度超限，终止抓取。")
                    return all_venues
                break

            pois = data.get("pois", [])
            total_count = int(data.get("count", 0))

            if not pois:
                print(f"  第{page}页无数据，结束当前关键词。")
                break

            # 逐条处理
            page_new_count = 0
            for poi in pois:
                poi_id = poi.get("id", "")

                # 全局去重（以 id 为唯一标识）
                if poi_id in seen_ids:
                    continue

                # 噪音过滤
                if is_noise(poi):
                    continue

                # 类别筛选
                if not should_keep_by_type(poi):
                    continue

                # 全部通过，收录
                seen_ids.add(poi_id)
                all_venues.append(extract_fields(poi))
                page_new_count += 1

            print(
                f"  第{page}页：共 {len(pois)} 条，"
                f"新增收录 {page_new_count} 条，"
                f"累计 {len(all_venues)} 条"
            )

            # 翻页终止条件：当前页不足 PAGE_SIZE 条，
            # 或者已拉取到总记录数
            if len(pois) < PAGE_SIZE or page * PAGE_SIZE >= total_count:
                print(f"  已翻至最后一页，结束关键词「{keyword}」。")
                break

            page += 1
            time.sleep(REQUEST_INTERVAL)

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
    print(f"目标城市：{CITY}")
    print(f"输出文件：{OUTPUT_CSV}")
    print("=" * 60)

    venues = fetch_all_venues()

    if not venues:
        print("\n未获取到任何有效数据，请检查 API Key 或网络连接。")
        return

    # 转为 DataFrame
    df = pd.DataFrame(venues)

    # === 对部分 typecode 分类做进一步人工规则补充 ===
    # 将 typecode 归入 99xxxx（不确定类别）的记录改为明确的零售类别，
    # 防止误保留纯商业场所（除非名字含"艺术空间"）
    def refine_type(row):
        typecode = row.get("typecode", "")
        name = row.get("name", "")

    # 核心防漏规则：如果名字里包含单字 "茶"，且它不是正规的文化馆（16开头）或景区（05开头）
    # 比如餐饮类(05/06)里面的"某某茶艺术空间"，直接剔除
        if "茶" in name and not typecode.startswith(("16", "05")):
            return False
    
        # 如果不是我们信任的大类，且名称不含"艺术空间"，标记为可疑
        if not typecode.startswith(("16", "05")) and not any(kw in name for kw in ["艺术空间", "画廊"]):
            return False  # 丢弃
        return True

    before = len(df)
    df = df[df.apply(refine_type, axis=1)]
    after = len(df)
    if before - after > 0:
        print(f"\n[二次清洗] 通过 typecode 规则又过滤了 {before - after} 条记录。")

    # 按行政区排序
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


if __name__ == "__main__":
    main()
