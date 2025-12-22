#!/usr/bin/python
import asyncio
import aiohttp
import re
import sys
import random
from utils import TABLE_MAP, TODAY, renew_doc, renew_readme, load_links, save_links

BASE_URL = "https://testflight.apple.com/"

FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")
APP_NAME_PATTERN = re.compile(r"Join the (.+) beta - TestFlight - Apple")
APP_NAME_CH_PATTERN = re.compile(r"加入 Beta 版“(.+)” - TestFlight - Apple")

async def check_status(session, key, retry=10):
    status = 'N'
    app_name = "None"
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    for i in range(retry):
        try:
            async with session.get(f'/join/{key}', headers={'User-Agent': ua}) as resp:
                if resp.status == 404:
                    return (key, 'D', app_name)
                resp.raise_for_status()
                resp_html = await resp.text()
                
                if NO_PATTERN.search(resp_html) is not None:
                    status = 'N'
                elif FULL_PATTERN.search(resp_html) is not None:
                    status = 'F'
                else:
                    status = 'Y'
                
                app_name_search = APP_NAME_PATTERN.search(resp_html)
                app_name_ch_search = APP_NAME_CH_PATTERN.search(resp_html)
                if app_name_search:
                    app_name = app_name_search.group(1)
                elif app_name_ch_search:
                    app_name = app_name_ch_search.group(1)
                
                return (key, status, app_name)
        except Exception as e:
            rand = round(random.random(), 3)
            print(f"[warn] {key} - {e}, wait {i*(rand+1)+1} s. Retry({i+1}/{retry})")
            await asyncio.sleep(i*(rand+1)+1)
    
    print(f"[error] Key ({key}) have max retries, return default value!")
    return (key, status, app_name)

async def main():
    if len(sys.argv) < 3:
        print("Usage: python add_link.py <testflight_link> <table> [app_name]")
        sys.exit(1)

    testflight_link = sys.argv[1]
    table = sys.argv[2].lower()
    app_name = sys.argv[3] if len(sys.argv) > 3 else "None"
    
    link_id_match = re.search(r"join/(.*)$", testflight_link, re.I)
    if link_id_match:
        testflight_link = link_id_match.group(1)
    
    if table not in TABLE_MAP or table == "signup":
        print(f"[Error] Invalid table: {table}. Exit...")
        sys.exit(1)

    conn_config = aiohttp.TCPConnector(limit=5, limit_per_host=2)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession(base_url=BASE_URL, connector=conn_config, headers=headers) as session:
        _, status, fetched_name = await check_status(session, testflight_link)
        if not app_name or app_name.lower() == "none":
            app_name = fetched_name

    links_data = load_links()
    if table not in links_data:
        links_data[table] = {}
    
    links_data[table][testflight_link] = {
        "app_name": app_name,
        "status": status,
        "last_modify": TODAY
    }
    save_links(links_data)
    print(f"[info] Added {app_name} to {table}")

    renew_doc(table, links_data)
    renew_readme()

if __name__ == "__main__":
    asyncio.run(main())
