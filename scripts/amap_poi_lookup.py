#!/usr/bin/env python3
"""输入商户名称，调用高德 POI 搜索 API，返回匹配结果和分类编码。"""

import argparse
import os
import sys

import requests

API_URL = "https://restapi.amap.com/v3/place/text"


def search_poi(key: str, keywords: str, city: str = ""):
    params = {
        "key": key,
        "keywords": keywords,
        "offset": 20,
        "page": 1,
        "extensions": "all",
    }
    if city:
        params["city"] = city

    resp = requests.get(API_URL, params=params, timeout=10)
    data = resp.json()

    if data.get("status") != "1":
        print(f"[ERROR] 高德 API 返回失败: {data.get('info', 'unknown')}")
        sys.exit(1)
    return data


def print_results(data: dict, keywords: str):
    count = int(data.get("count", 0))
    pois = data.get("pois", [])

    print("=" * 60)
    print(f"  查询: {keywords}")
    print(f"  匹配结果数: {count}")
    print("=" * 60)

    if not pois:
        print("  未找到匹配的 POI。")
        return

    for i, poi in enumerate(pois, 1):
        name = poi.get("name", "N/A")
        typecode = poi.get("typecode", "N/A")
        _type = poi.get("type", "N/A")
        address = poi.get("address", "")
        location = poi.get("location", "")
        pname = poi.get("pname", "")
        cityname = poi.get("cityname", "")
        adname = poi.get("adname", "")
        biz_area = poi.get("business_area", "")

        print(f"\n{'─' * 50}")
        print(f"  [{i}] {name}")
        print(f"      分类:       {_type}")
        print(f"      分类编码:   {typecode}")
        print(f"      地址:       {address}")
        print(f"      区域:       {pname} {cityname} {adname}")
        if biz_area:
            print(f"      商圈:       {biz_area}")
        print(f"      坐标:       {location}")


def main():
    parser = argparse.ArgumentParser(description="高德 POI 搜索 —— 按商户名称查询分类编码")
    parser.add_argument("--name", required=True,
                        help="商户名称，例如 故宫博物院")
    parser.add_argument("--city", default="",
                        help="城市，例如 北京（可选）")
    parser.add_argument("--key",
                        help="高德 API Key，默认读取 AMAP_KEY 环境变量")
    args = parser.parse_args()

    key = args.key or os.environ.get("AMAP_KEY")
    if not key:
        print("[ERROR] 请提供高德 API Key (通过 --key 参数或 AMAP_KEY 环境变量)")
        sys.exit(1)

    data = search_poi(key, args.name, args.city)
    print_results(data, args.name)


if __name__ == "__main__":
    main()