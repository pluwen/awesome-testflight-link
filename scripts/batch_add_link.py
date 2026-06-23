#!/usr/bin/python
"""
Batch add TestFlight links with a shared platform.
Accepts multiple links (one per line) and applies the same platform to all.
Optimized for GitHub Actions environment.
"""
import asyncio
import aiohttp
import re
import sys
import random
from utils import TODAY, renew_readme, load_links, save_links

BASE_URL = "https://testflight.apple.com/"

FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")
APP_NAME_PATTERN = re.compile(r"Join the (.+) beta - TestFlight - Apple")
APP_NAME_CH_PATTERN = re.compile(r'加入 Beta 版"(.+)" - TestFlight - Apple')


def parse_platforms_from_string(s: str) -> list:
    """Parse comma-separated platform string into validated list."""
    if not s:
        return []
    parts = [p.strip().lower() for p in s.split(',') if p.strip()]
    valid = {'ios', 'ipados', 'macos', 'tvos', 'visionos'}
    return [p for p in parts if p in valid]


def parse_links(raw: str) -> list[str]:
    """Extract link IDs from a multi-line/comma-separated raw string."""
    link_ids = []
    for line in raw.replace(',', '\n').splitlines():
        line = line.strip()
        if not line:
            continue
        # Support full URLs or just the join code
        match = re.search(r"join/([A-Za-z0-9]+)$", line, re.I)
        if match:
            link_ids.append(match.group(1))
        elif re.fullmatch(r"[A-Za-z0-9]+", line):
            link_ids.append(line)
    return link_ids


async def check_status(session, key, retry=10):
    """Fetch status and app name for a single link."""
    app_name = ""
    ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    for i in range(retry):
        try:
            async with session.get(
                f'/join/{key}',
                headers={'User-Agent': ua},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 404:
                    return (key, 'D', app_name)

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

                return (key, status, app_name)
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
    return (key, 'N', app_name)


async def main():
    args = sys.argv[1:]

    if len(args) < 2:
        print("Usage: python batch_add_link.py <links_file_or_raw> <platforms>")
        print()
        print("Batch add multiple TestFlight links that share the same platform(s).")
        print()
        print("Arguments:")
        print("  links   - A file path containing links (one per line),")
        print("            or a string with links separated by newlines / commas")
        print("  platforms - Comma-separated platforms (e.g. ios,ipados,macos,tvos,visionos)")
        print()
        print("Examples:")
        print("  python3 batch_add_link.py links.txt ios")
        print("  python3 batch_add_link.py 'AbcXYZ,Def123,Ghi456' ios,ipados")
        print()
        print("  File format (links.txt):")
        print("    https://testflight.apple.com/join/AbcXYZ")
        print("    https://testflight.apple.com/join/Def123")
        print("    Ghi456")
        sys.exit(1)

    raw_input = args[0]
    platforms_str = args[1]

    # Parse platforms
    tables = parse_platforms_from_string(platforms_str)
    if not tables:
        print(f"[error] No valid platforms found in: '{platforms_str}'")
        print("Valid platforms: ios, ipados, macos, tvos, visionos")
        sys.exit(1)

    # Parse links: try file first, then treat as raw string
    from pathlib import Path
    input_path = Path(raw_input)
    if input_path.is_file():
        print(f"[info] Reading links from file: {input_path}")
        raw_links = input_path.read_text(encoding='utf-8')
    else:
        raw_links = raw_input

    link_ids = parse_links(raw_links)
    if not link_ids:
        print("[error] No valid TestFlight links found in input")
        sys.exit(1)

    # Deduplicate while preserving order
    seen = set()
    unique_links = []
    for lid in link_ids:
        if lid not in seen:
            seen.add(lid)
            unique_links.append(lid)
    link_ids = unique_links

    print(f"[info] Batch adding {len(link_ids)} link(s) for platform(s): {', '.join(tables)}")

    # Fetch status for all links concurrently
    conn_config = aiohttp.TCPConnector(limit=5, limit_per_host=2)
    async with aiohttp.ClientSession(base_url=BASE_URL, connector=conn_config) as session:
        tasks = [check_status(session, key) for key in link_ids]
        results = await asyncio.gather(*tasks)

    # Load existing data
    links_data = load_links()
    if "_links" not in links_data:
        links_data["_links"] = {}

    added_count = 0
    updated_count = 0
    skipped_count = 0

    for key, status, app_name in results:
        if key is None:
            continue

        # Fall back to a placeholder if the name could not be extracted.
        if not app_name:
            app_name = "Unknown"
            print(f"  [warn] Could not extract app name for {key}, using '{app_name}'")

        link_info = links_data["_links"].get(key)

        if link_info is None:
            links_data["_links"][key] = {
                "app_name": app_name,
                "status": status,
                "tables": tables,
                "last_modify": TODAY,
            }
            added_count += 1
            print(f"  [+] {app_name} ({key}) → {status}")
        else:
            # Update existing link
            old_platforms = link_info.get("tables", [])

            # Merge platforms: keep existing + add new ones
            merged = list(dict.fromkeys(old_platforms + tables))

            link_info["app_name"] = app_name
            link_info["status"] = status
            link_info["tables"] = merged
            link_info["last_modify"] = TODAY

            if set(old_platforms) != set(merged):
                print(f"  [~] {app_name} ({key}) → {status}, platforms: {old_platforms} → {merged}")
            else:
                print(f"  [=] {app_name} ({key}) → {status} (updated)")
            updated_count += 1

    save_links(links_data)
    print()
    print(f"[info] Batch complete: {added_count} added, {updated_count} updated, {len(link_ids)} total")

    # Regenerate README
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
