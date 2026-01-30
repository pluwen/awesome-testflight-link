#!/usr/bin/python
import sys
import re
from utils import renew_readme, load_links, save_links

def main():
    if len(sys.argv) < 2:
        print("Usage: python del_link.py <testflight_link>")
        print()
        print("Examples:")
        print("  python3 del_link.py NXLBigzY")
        print("  python3 del_link.py https://testflight.apple.com/join/NXLBigzY")
        sys.exit(1)

    testflight_link = sys.argv[1]

    # Extract link ID from URL if needed
    link_id_match = re.search(r"join/(.*)$", testflight_link, re.I)
    if link_id_match:
        testflight_link = link_id_match.group(1)

    links_data = load_links()
    all_links = links_data.get("_links", {})
    
    if testflight_link not in all_links:
        print(f"[warn] Link {testflight_link} not found")
        return

    link_info = all_links[testflight_link]
    app_name = link_info.get("app_name", "Unknown")
    
    # Delete the entire link
    del links_data["_links"][testflight_link]
    print(f"[info] Deleted '{app_name}' ({testflight_link})")

    save_links(links_data)
    
    # Regenerate README
    renew_readme()

if __name__ == "__main__":
    main()
