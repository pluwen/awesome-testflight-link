#!/usr/bin/python
import sys
import re
from utils import TABLE_MAP, renew_doc, renew_readme, load_links, save_links

def main():
    if len(sys.argv) < 3:
        print("Usage: python del_link.py <testflight_link> <table>")
        sys.exit(1)

    testflight_link = sys.argv[1]
    table = sys.argv[2].lower()

    link_id_match = re.search(r"join/(.*)$", testflight_link, re.I)
    if link_id_match:
        testflight_link = link_id_match.group(1)

    if table not in TABLE_MAP:
        print(f"[Error] Invalid table: {table}. Exit...")
        sys.exit(1)

    links_data = load_links()
    if table in links_data and testflight_link in links_data[table]:
        del links_data[table][testflight_link]
        save_links(links_data)
        print(f"[info] Deleted {testflight_link} from {table}")
    else:
        print(f"[warn] Link {testflight_link} not found in {table}")

    renew_doc(table, links_data)
    renew_readme()

if __name__ == "__main__":
    main()
