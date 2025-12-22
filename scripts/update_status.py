#!/usr/bin/python
import asyncio
import aiohttp
import re
import random
from utils import TABLE_MAP, TODAY, renew_doc, renew_readme, load_links, save_links

BASE_URL = "https://testflight.apple.com/"
FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")

async def check_status(session, key, current_status, retry=5):
    for i in range(retry):
        try:
            # 使用固定的现代浏览器 User-Agent，避免 fake_user_agent 可能产生的问题
            ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            async with session.get(f'/join/{key}', headers={'User-Agent': ua}) as resp:
                if resp.status == 404:
                    print(f"[info] {key} - 404 Deleted")
                    return (key, 'D')
                
                resp.raise_for_status()
                resp_html = await resp.text()
                
                if NO_PATTERN.search(resp_html) is not None:
                    return (key, 'N')
                elif FULL_PATTERN.search(resp_html) is not None:
                    return (key, 'F')
                else:
                    # 额外检查是否包含 "Join the ... beta" 或 "Start Testing" 以确认是有效页面
                    if "TestFlight" in resp_html:
                        return (key, 'Y')
                    else:
                        print(f"[warn] {key} - Unexpected HTML content, keeping {current_status}")
                        return (key, current_status)
        except Exception as e:
            print(f"[warn] {key} - {e}, retry {i+1}/{retry}")
            await asyncio.sleep(i + random.random())
    
    print(f"[error] Failed to get status for {key} after {retry} retries, keeping current status: {current_status}")
    return (key, current_status)

async def update_table(table, links_data):
    print(f"[info] Updating table: {table}")
    table_data = links_data.get(table, {})
    links = list(table_data.keys())

    if not links:
        return

    conn_config = aiohttp.TCPConnector(limit=5, limit_per_host=2)
    async with aiohttp.ClientSession(base_url=BASE_URL, connector=conn_config) as session:
        tasks = [check_status(session, link, table_data[link].get('status', 'N')) for link in links]
        results = await asyncio.gather(*tasks)

    for link, status in results:
        if link in table_data:
            if table_data[link]['status'] != status:
                table_data[link]['status'] = status
                table_data[link]['last_modify'] = TODAY

    renew_doc(table, links_data)

async def main():
    links_data = load_links()
    for table in TABLE_MAP:
        if table == "signup":
            continue
        await update_table(table, links_data)
    
    save_links(links_data)
    renew_readme()

if __name__ == "__main__":
    asyncio.run(main())
