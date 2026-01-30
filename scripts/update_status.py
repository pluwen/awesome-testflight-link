#!/usr/bin/python
import asyncio
import aiohttp
import re
import random
from utils import TODAY, renew_readme, load_links, save_links
# Platform detection removed — platforms are managed manually

BASE_URL = "https://testflight.apple.com/"
FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")

async def check_status(session, key, current_status, app_name=None, retry=5):
    """获取应用状态和检测支持的平台"""
    for i in range(retry):
        try:
            ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            async with session.get(f'/join/{key}', headers={'User-Agent': ua}) as resp:
                if resp.status == 404:
                    print(f"[info] {key} - 404 Deleted")
                    return (key, 'D', set())
                
                resp.raise_for_status()
                resp_html = await resp.text()
                
                # 平台检测已移除；保持空集合以保持接口兼容
                detected_platforms = set()
                
                # 检测状态
                if NO_PATTERN.search(resp_html):
                    return (key, 'N', detected_platforms)
                elif FULL_PATTERN.search(resp_html):
                    return (key, 'F', detected_platforms)
                elif "TestFlight" in resp_html:
                    return (key, 'Y', detected_platforms)
                else:
                    print(f"[warn] {key} - Unexpected HTML content")
                    return (key, current_status, detected_platforms)
        except Exception as e:
            print(f"[warn] {key} - {e}, retry {i+1}/{retry}")
            await asyncio.sleep(i + random.random())
    
    print(f"[error] Failed to get status for {key} after {retry} retries")
    return (key, current_status, set())

async def update_all_links(links_data):
    """更新所有链接的状态和平台信息"""
    print(f"[info] Updating all links and detecting platforms...")
    all_links = links_data.get("_links", {})
    links = list(all_links.keys())

    if not links:
        print("[warn] No links found")
        return

    conn_config = aiohttp.TCPConnector(limit=5, limit_per_host=2)
    async with aiohttp.ClientSession(base_url=BASE_URL, connector=conn_config) as session:
        tasks = [
            check_status(session, link, all_links[link].get('status', 'N'), all_links[link].get('app_name')) 
            for link in links
        ]
        results = await asyncio.gather(*tasks)

    updated_count = 0

    for link, status, _ in results:
        if link not in all_links:
            continue

        link_info = all_links[link]

        # 仅更新状态，不修改平台信息
        if link_info.get('status') != status:
            link_info['status'] = status
            link_info['last_modify'] = TODAY
            updated_count += 1

    print(f"[info] Status updated: {updated_count}")

async def main():
    links_data = load_links()
    await update_all_links(links_data)
    
    save_links(links_data)
    
    # 直接生成 README
    renew_readme()

if __name__ == "__main__":
    asyncio.run(main())
