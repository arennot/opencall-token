#!/usr/bin/env python3
"""将现有 app.js 中的 25 条硬编码数据导入 Supabase。"""
import json, os, re, sys
from supabase import create_client


def extract_opportunities(appjs_path):
    with open(appjs_path, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"const opportunities = (\[.+?\]);", content, re.DOTALL)
    if not match:
        print("Error: Could not find opportunities array")
        sys.exit(1)
    json_str = match.group(1)
    json_str = re.sub(r",\s*\]", "]", json_str)
    json_str = json_str.replace("undefined", "null")
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        sys.exit(1)


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)
    appjs_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "opencall-token", "app.js")
    opportunities = extract_opportunities(appjs_path)
    print(f"Found {len(opportunities)} opportunities")
    supabase = create_client(url, key)
    inserted = skipped = 0
    for opp in opportunities:
        record = {
            "title": opp.get("title", ""),
            "type": opp.get("type", "opencall"),
            "organization": opp.get("organization", ""),
            "deadline": opp.get("deadline") or None,
            "location": opp.get("location") or None,
            "disciplines": opp.get("disciplines", []),
            "funding": opp.get("funding") or None,
            "description": opp.get("description") or None,
            "url": opp.get("url") or None,
            "source": opp.get("source", "manual"),
            "posted_at": opp.get("posted_at") or None,
            "featured": opp.get("featured", False),
            "is_local": opp.get("_local", False),
            "status": "published",
        }
        if record["url"]:
            existing = supabase.table("opportunities").select("id").eq("url", record["url"]).execute()
            if existing.data and len(existing.data) > 0:
                print(f"  Skipped: {record['title']}")
                skipped += 1
                continue
        result = supabase.table("opportunities").insert(record).execute()
        if result.data:
            print(f"  Inserted: {record['title']} ({record['type']})")
            inserted += 1
        else:
            print(f"  Failed: {record['title']}")
    print(f"\nDone! Inserted: {inserted}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
