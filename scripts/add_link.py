#!/usr/bin/python
"""
Add TestFlight links with manual platform input.
Optimized for GitHub Actions environment.
"""
import asyncio
import aiohttp
import re
import sys
import random
from utils import TODAY, renew_readme, load_links, save_links
import os

BASE_URL = "https://testflight.apple.com/"

FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")
APP_NAME_PATTERN = re.compile(r"Join the (.+) beta - TestFlight - Apple")
APP_NAME_CH_PATTERN = re.compile(r'加入 Beta 版"(.+)" - TestFlight - Apple')

# Parse comma-separated platform string from CLI or env
def parse_platforms_from_string(s: str) -> list:
    """Parse comma-separated platform string into validated list."""
    if not s:
        return []
    parts = [p.strip().lower() for p in s.split(',') if p.strip()]
    valid = {'ios', 'ipados', 'macos', 'tvos'}
    return [p for p in parts if p in valid]

async def check_status(session, key, retry=10):
    app_name = "None"
    html_content = ""
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    for i in range(retry):
        try:
            async with session.get(f'/join/{key}', headers={'User-Agent': ua}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 404:
                    return (key, 'D', app_name, "")
                resp.raise_for_status()
                html_content = await resp.text()

                if NO_PATTERN.search(html_content) is not None:
                    status = 'N'
                elif FULL_PATTERN.search(html_content) is not None:
                    status = 'F'
                else:
                    status = 'Y'

                app_name_search = APP_NAME_PATTERN.search(html_content)
                app_name_ch_search = APP_NAME_CH_PATTERN.search(html_content)
                if app_name_search:
                    app_name = app_name_search.group(1)
                elif app_name_ch_search:
                    app_name = app_name_ch_search.group(1)

                return (key, status, app_name, html_content)
        except asyncio.TimeoutError:
            if i < retry - 1:
                wait_time = 2 ** i
                print(f"[warn] {key} - Timeout, waiting {wait_time}s before retry ({i+1}/{retry})")
                await asyncio.sleep(wait_time)
        except Exception as e:
            if i < retry - 1:
                wait_time = 2 ** i
                print(f"[warn] {key} - {type(e).__name__}, waiting {wait_time}s before retry ({i+1}/{retry})")
                await asyncio.sleep(wait_time)

    print(f"[warn] {key} - Failed after {retry} retries, using default values")
    return (key, status, app_name, "")

async def main():
    # Parse arguments - link, platforms (comma-separated), and optional app_name
    args = sys.argv[1:]

    if len(args) < 1:
        print("Usage: python add_link.py <link> <platforms> [app_name]")
        print()
        print("Examples:")
        print("  python3 add_link.py AbcXYZ ios")
        print("  python3 add_link.py AbcXYZ ios,ipados,macos")
        print("  python3 add_link.py AbcXYZ ios 'Day One Journal'")
        print()
        print("Note: Platforms must be provided (comma-separated, e.g. ios,ipados,macos,tvos)")
        sys.exit(1)

    testflight_link = args[0]
    # If platforms provided as second arg, app_name may be third arg
    if len(args) > 2:
        app_name = args[2]
    else:
        app_name = None

    # Extract link ID from URL
    link_id_match = re.search(r"join/(.*)$", testflight_link, re.I)
    if link_id_match:
        testflight_link = link_id_match.group(1)

    # Fetch page info
    conn_config = aiohttp.TCPConnector(limit=5, limit_per_host=2)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with aiohttp.ClientSession(base_url=BASE_URL, connector=conn_config, headers=headers) as session:
        _, status, fetched_name, html_content = await check_status(session, testflight_link)

        if not app_name or app_name.lower() == "none":
            app_name = fetched_name

        # Determine platforms: prefer PLATFORMS env, then CLI arg
        platforms_from_env = None
        env_val = os.getenv('PLATFORMS')
        if env_val:
            platforms_from_env = parse_platforms_from_string(env_val)

        # CLI: second arg is platforms (comma separated), third arg is app_name
        cli_platforms = None
        if len(args) >= 2:
            cli_platforms = parse_platforms_from_string(args[1])

        if cli_platforms:
            tables = cli_platforms
            print(f"[info] Using platforms from CLI arg: {', '.join(tables)}")
        elif platforms_from_env:
            tables = platforms_from_env
            print(f"[info] Using platforms from PLATFORMS env: {', '.join(tables)}")
        else:
            print("[error] No platforms specified. Please provide platforms as the second argument or set PLATFORMS env.")
            print("Usage: python add_link.py <link> <platforms_comma_separated> [app_name]")
            sys.exit(1)

    # Load and update data
    links_data = load_links()
    if "_links" not in links_data:
        links_data["_links"] = {}

    # Check if link already exists
    link_exists = testflight_link in links_data["_links"]
    link_info = links_data["_links"].get(testflight_link)

    if link_info is None:
        link_info = {
            "app_name": app_name,
            "status": status,
            "tables": tables,
            "last_modify": TODAY
        }
        action = "Added new link"
    else:
        old_platforms = link_info.get("tables", [])
        link_info["app_name"] = app_name
        link_info["status"] = status
        link_info["tables"] = tables  # Replace with provided platforms
        link_info["last_modify"] = TODAY

        # Log platform changes if they differ
        if set(old_platforms) != set(tables):
            print(f"[info] Updated platforms for '{app_name}': {old_platforms} → {tables}")

        action = "Updated existing link"

    links_data["_links"][testflight_link] = link_info
    save_links(links_data)
    print(f"[info] {action} '{app_name}' with platforms: {', '.join(link_info['tables'])}")

    # 直接生成 README
    renew_readme()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[info] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"[error] {type(e).__name__}: {e}")
        sys.exit(1)
