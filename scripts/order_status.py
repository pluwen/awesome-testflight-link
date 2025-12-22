#!/usr/bin/python
from utils import TABLE_MAP, renew_doc, renew_readme, load_links

def main():
    links_data = load_links()
    for table in TABLE_MAP:
        if table == "signup":
            continue
        print(f"[info] Ordering status for table: {table}")
        renew_doc(table, links_data)
    renew_readme()

if __name__ == "__main__":
    main()
