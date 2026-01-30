#!/usr/bin/python
import sys
import re
from utils import TABLE_MAP, renew_readme, load_links, save_links

def main():
    if len(sys.argv) < 3:
        print("Usage: python del_link.py <testflight_link> <table1>[,table2,table3...]")
        print("To delete from all tables, use: python del_link.py <testflight_link> all")
        sys.exit(1)

    testflight_link = sys.argv[1]
    tables_str = sys.argv[2].lower()

    link_id_match = re.search(r"join/(.*)$", testflight_link, re.I)
    if link_id_match:
        testflight_link = link_id_match.group(1)

    links_data = load_links()
    all_links = links_data.get("_links", {})
    
    if testflight_link not in all_links:
        print(f"[warn] Link {testflight_link} not found")
        return

    link_info = all_links[testflight_link]
    
    # Parse which tables to delete from
    if tables_str == "all":
        # Delete the entire link
        del links_data["_links"][testflight_link]
        print(f"[info] Deleted {testflight_link} from all tables")
        affected_tables = link_info.get("tables", [])
    else:
        # Delete from specific tables
        tables = [t.strip() for t in tables_str.split(',')]
        
        # Validate all tables
        for table in tables:
            if table not in TABLE_MAP:
                print(f"[Error] Invalid table: {table}. Exit...")
                sys.exit(1)
        
        affected_tables = []
        for table in tables:
            if table in link_info.get("tables", []):
                link_info["tables"].remove(table)
                affected_tables.append(table)
        
        # If no tables left, delete the entire link
        if not link_info.get("tables", []):
            del links_data["_links"][testflight_link]
            print(f"[info] Deleted {testflight_link} from all tables")
        else:
            print(f"[info] Deleted {testflight_link} from {', '.join(affected_tables)}")

    save_links(links_data)
    
    # 直接生成 README
    renew_readme()

if __name__ == "__main__":
    main()
