#!/usr/bin/python
"""
Add TestFlight links with optional auto platform detection.
Optimized for GitHub Actions environment.
"""
import asyncio
import aiohttp
import re
import sys
import random
from utils import TABLE_MAP, TODAY, renew_readme, load_links, save_links

BASE_URL = "https://testflight.apple.com/"

FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")
APP_NAME_PATTERN = re.compile(r"Join the (.+) beta - TestFlight - Apple")
APP_NAME_CH_PATTERN = re.compile(r'加入 Beta 版"(.+)" - TestFlight - Apple')

# Simple platform keywords for detection
PLATFORM_KEYWORDS = {
    'ios': ['iphone', 'ios', 'requires ios'],
    'ipados': ['ipad', 'ipados', 'requires ipados'],
    'macos': ['macos', 'mac app', 'requires macos'],
    'tvos': ['tvos', 'apple tv', 'tv app'],
}

async def check_status(session, key, retry=10):
    """Fetch TestFlight page and extract app info."""
    status = 'N'
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

def detect_platforms_simple(html_content: str) -> list:
    """
    Simple platform detection using keyword matching.
    Returns list of detected platform categories.
    """
    if not html_content:
        return []
    
    detected = []
    html_lower = html_content.lower()
    
    # Check each platform
    for platform, keywords in PLATFORM_KEYWORDS.items():
        for keyword in keywords:
            if keyword in html_lower:
                detected.append(platform)
                break
    
    return detected

async def main():
    # Parse arguments
    auto_detect = "--auto" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--auto"]
    
    if len(args) < 1:
        print("Usage: python add_link.py [--auto] <link> [categories] [app_name]")
        print()
        print("Examples:")
        print("  # Manual category specification (recommended for CI/CD)")
        print("  python3 add_link.py AbcXYZ ios,macos")
        print("  python3 add_link.py AbcXYZ ipados")
        print()
        print("  # Auto-detect platforms (requires network access)")
        print("  python3 add_link.py --auto AbcXYZ")
        print("  python3 add_link.py --auto AbcXYZ 'App Name'")
        print()
        print("Available categories: ios, ipados, macos, tvos")
        sys.exit(1)
    
    testflight_link = args[0]
    tables = None
    app_name = None
    
    if auto_detect:
        # Format: --auto <link> [app_name]
        app_name = args[1] if len(args) > 1 else None
    else:
        # Format: <link> [categories] [app_name]
        if len(args) >= 2:
            tables = [t.strip() for t in args[1].split(',')]
        if len(args) >= 3:
            app_name = args[2]
    
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
        
        # Handle auto-detection
        if auto_detect:
            tables = detect_platforms_simple(html_content)
            if tables:
                print(f"[info] Auto-detected categories: {', '.join(tables)}")
            else:
                print(f"[warn] Could not detect platforms, defaulting to iOS")
                tables = ['ios']
        
        # Validate categories
        if not tables:
            print(f"[Error] No categories specified. Exit...")
            sys.exit(1)
        
        for table in tables:
            if table not in TABLE_MAP or table == "signup":
                print(f"[Error] Invalid category: {table}. Exit...")
                sys.exit(1)
    
    # Load and update data
    links_data = load_links()
    if "_links" not in links_data:
        links_data["_links"] = {}
    
    # Check if link already exists
    link_info = links_data["_links"].get(testflight_link)
    if link_info is None:
        link_info = {
            "app_name": app_name,
            "status": status,
            "tables": [],
            "last_modify": TODAY
        }
    else:
        link_info["app_name"] = app_name
        link_info["status"] = status
        link_info["last_modify"] = TODAY
    
    # Add tables (avoid duplicates)
    for table in tables:
        if table not in link_info["tables"]:
            link_info["tables"].append(table)
    
    links_data["_links"][testflight_link] = link_info
    save_links(links_data)
    print(f"[info] Added '{app_name}' to categories: {', '.join(link_info['tables'])}")
    
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
