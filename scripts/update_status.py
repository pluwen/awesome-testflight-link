#!/usr/bin/python
import asyncio
import aiohttp
import re
import random
from utils import TABLE_MAP, TODAY, renew_doc, renew_readme, load_links, save_links
from platform_detector import detect_platforms

BASE_URL = "https://testflight.apple.com/"
FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")

async def check_status(session, key, current_status, app_name=None, retry=5):
    for i in range(retry):
        try:
            # 使用固定的现代浏览器 User-Agent，避免 fake_user_agent 可能产生的问题
            ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            async with session.get(f'/join/{key}', headers={'User-Agent': ua}) as resp:
                if resp.status == 404:
                    print(f"[info] {key} - 404 Deleted")
                    return (key, 'D', None)
                
                resp.raise_for_status()
                resp_html = await resp.text()
                
                # 自动检测平台
                detected_platforms = detect_platforms(resp_html, app_name)
                
                if NO_PATTERN.search(resp_html) is not None:
                    return (key, 'N', detected_platforms)
                elif FULL_PATTERN.search(resp_html) is not None:
                    return (key, 'F', detected_platforms)
                else:
                    # 额外检查是否包含 "Join the ... beta" 或 "Start Testing" 以确认是有效页面
                    if "TestFlight" in resp_html:
                        return (key, 'Y', detected_platforms)
                    else:
                        print(f"[warn] {key} - Unexpected HTML content, keeping {current_status}")
                        return (key, current_status, detected_platforms)
        except Exception as e:
            print(f"[warn] {key} - {e}, retry {i+1}/{retry}")
            await asyncio.sleep(i + random.random())
    
    print(f"[error] Failed to get status for {key} after {retry} retries, keeping current status: {current_status}")
    return (key, current_status, None)

async def update_all_links(links_data):
    print(f"[info] Updating all links")
    all_links = links_data.get("_links", {})
    links = list(all_links.keys())

    if not links:
        return

    conn_config = aiohttp.TCPConnector(limit=5, limit_per_host=2)
    async with aiohttp.ClientSession(base_url=BASE_URL, connector=conn_config) as session:
        tasks = [
            check_status(session, link, all_links[link].get('status', 'N'), all_links[link].get('app_name', None)) 
            for link in links
        ]
        results = await asyncio.gather(*tasks)

    for link, status, detected_platforms in results:
        if link in all_links:
            # 更新状态
            if all_links[link]['status'] != status:
                all_links[link]['status'] = status
                all_links[link]['last_modify'] = TODAY
            
            # 更新平台信息（如果检测到）
            if detected_platforms:
                current_tables = set(all_links[link].get("tables", []))
                detected_set = set(detected_platforms)
                
                # 如果检测到的平台与当前不同，更新它
                if current_tables != detected_set:
                    all_links[link]['tables'] = sorted(list(detected_set))
                    all_links[link]['last_modify'] = TODAY
                    print(f"[info] {link} - Updated platforms to: {', '.join(all_links[link]['tables'])}")

async def main():
    links_data = load_links()
    await update_all_links(links_data)
    
    save_links(links_data)
    
    # 直接生成 README
    renew_readme()

if __name__ == "__main__":
    asyncio.run(main())
