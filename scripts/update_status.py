#!/usr/bin/python
import asyncio
import aiohttp
from utils import (
    BASE_URL,
    MISSING_NAMES,
    TODAY,
    check_testflight_status,
    renew_readme,
    load_links,
    save_links,
)

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
            check_testflight_status(
                session,
                link,
                all_links[link].get('status', 'N'),
                all_links[link].get('app_name'),
            )
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
