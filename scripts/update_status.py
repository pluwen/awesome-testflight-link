#!/usr/bin/python
import asyncio
import aiohttp
import re
import random
from fake_user_agent import user_agent
from utils import TABLE_MAP, TODAY, renew_doc, renew_readme, load_links, save_links

BASE_URL = "https://testflight.apple.com/"
FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")

async def check_status(session, key, retry=5):
    status = 'N'
    for i in range(retry):
        try:
            async with session.get(f'/join/{key}', headers={'User-Agent': user_agent()}) as resp:
                if resp.status == 404:
                    return (key, 'D')
                resp.raise_for_status()
                resp_html = await resp.text()
                
                if NO_PATTERN.search(resp_html) is not None:
                    status = 'N'
                elif FULL_PATTERN.search(resp_html) is not None:
                    status = 'F'
                else:
                    status = 'Y'
                return (key, status)
        except Exception as e:
            await asyncio.sleep(i + random.random())
    return (key, status)

async def update_table(table, links_data):
    print(f"[info] Updating table: {table}")
    table_data = links_data.get(table, {})
    links = list(table_data.keys())

    if not links:
        return

    conn_config = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(BASE_URL, connector=conn_config) as session:
        tasks = [check_status(session, link) for link in links]
        results = await asyncio.gather(*tasks)

    for link, status in results:
        if link in table_data:
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
