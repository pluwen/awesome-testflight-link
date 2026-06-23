#!/usr/bin/python
import asyncio
import aiohttp
import re
import random
from utils import TODAY, renew_readme, load_links, save_links

BASE_URL = "https://testflight.apple.com/"
FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")
APP_NAME_PATTERN = re.compile(r"Join the (.+) beta - TestFlight - Apple")
APP_NAME_CH_PATTERN = re.compile(r'加入 Beta 版"(.+)" - TestFlight - Apple')

# App names that should be treated as "missing" and re-extracted when possible.
MISSING_NAMES = {"", "None", "none", "Unknown"}

async def check_status(session, key, current_status, app_name=None, retry=5):
    """获取应用状态，并尝试补全缺失的应用名称"""
    for i in range(retry):
        try:
            ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            async with session.get(f'/join/{key}', headers={'User-Agent': ua}) as resp:
                if resp.status == 404:
                    print(f"[info] {key} - 404 Deleted")
                    return (key, 'D', app_name)

                resp.raise_for_status()
                resp_html = await resp.text()

                # 提取应用名称
                fetched_name = ""
                app_name_search = APP_NAME_PATTERN.search(resp_html)
                app_name_ch_search = APP_NAME_CH_PATTERN.search(resp_html)
                if app_name_search:
                    fetched_name = app_name_search.group(1)
                elif app_name_ch_search:
                    fetched_name = app_name_ch_search.group(1)

                # 仅当原名称缺失或占位时，才用新抓取的名称补全
                new_name = app_name
                if (not app_name or app_name in MISSING_NAMES) and fetched_name:
                    new_name = fetched_name

                # 检测状态
                if NO_PATTERN.search(resp_html):
                    return (key, 'N', new_name)
                elif FULL_PATTERN.search(resp_html):
                    return (key, 'F', new_name)
                elif "TestFlight" in resp_html:
                    return (key, 'Y', new_name)
                else:
                    print(f"[warn] {key} - Unexpected HTML content")
                    return (key, current_status, app_name)
        except Exception as e:
            print(f"[warn] {key} - {e}, retry {i+1}/{retry}")
            await asyncio.sleep(i + random.random())

    print(f"[error] Failed to get status for {key} after {retry} retries")
    return (key, current_status, app_name)

async def update_all_links(links_data):
    """更新所有链接的状态，并补全缺失的应用名称"""
    print(f"[info] Updating all links...")
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

    for link, status, app_name in results:
        if link not in all_links:
            continue

        link_info = all_links[link]
        changed = False

        if link_info.get('status') != status:
            link_info['status'] = status
            link_info['last_modify'] = TODAY
            changed = True

        # 补全缺失/占位的应用名称
        if app_name and app_name not in MISSING_NAMES:
            old_name = link_info.get('app_name')
            if not old_name or old_name in MISSING_NAMES:
                link_info['app_name'] = app_name
                changed = True
                print(f"[info] {link} - filled app name: '{old_name}' → '{app_name}'")

        if changed:
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
