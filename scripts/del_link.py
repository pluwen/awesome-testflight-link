#!/usr/bin/python
'''
Author       : tom-snow
Date         : 2022-03-16 19:32:32
LastEditTime : 2022-04-24 17:27:30
LastEditors  : tom-snow
Description  : 
FilePath     : /awesome-testflight-link/scripts/del_link.py
'''

import sqlite3
import re, os, sys

TABLE_MAP = {
    "macos": "./data/macos.md",
    "ios": "./data/ios.md",
    "tvos": "./data/tvos.md",
    "ios_game": "./data/ios_game.md",
    "chinese": "./data/chinese.md",
    "signup": "./data/signup.md"
}
README_TEMPLATE_FILE = "./data/README.template"


def renew_doc(data_file, table):
    # Read title from existing file (first line)
    title = ""
    try:
        with open(data_file, 'r') as f:
            title = f.readline().strip()
    except Exception:
        title = os.path.basename(data_file)

    # Connect to database and get apps by status
    conn = sqlite3.connect('../db/sqlite3.db')
    cur = conn.cursor()

    status_info = {
        'Y': {'name': 'Available', 'description': 'Apps currently accepting new testers'},
        'F': {'name': 'Full', 'description': 'Apps that have reached their tester limit'},
        'N': {'name': 'No', 'description': 'Apps not currently accepting testers'},
        'D': {'name': 'Removed', 'description': 'Apps that have been removed from TestFlight'}
    }

    markdown = [f"{title}\n\n"]

    for status_code in ['Y', 'F', 'N', 'D']:
        status_data = status_info[status_code]
        res = cur.execute(f"""SELECT app_name, testflight_link, status, last_modify FROM {table} 
                             WHERE status = ? ORDER BY app_name""", (status_code,))
        apps = res.fetchall()

        if apps:
            app_count = len(apps)
            markdown.append(f"<details>\n")
            markdown.append(f"<summary><strong>{status_data['name']} ({app_count} app{'s' if app_count != 1 else ''})</strong> - {status_data['description']}</summary>\n\n")

            if status_code == 'Y' and app_count > 0:
                markdown.append(f"_✅ These {app_count} apps are currently accepting new testers! Click the links to join._\n\n")
            elif status_code == 'F' and app_count > 0:
                markdown.append(f"_⚠️ These {app_count} apps have reached their tester limit. Try checking back later._\n\n")

            markdown.append("| Name | TestFlight Link | Status | Last Updated |\n")
            markdown.append("| --- | --- | --- | --- |\n")

            for app_name, testflight_link, status, last_modify in apps:
                full_link = f"https://testflight.apple.com/join/{testflight_link}"
                markdown_link = f"[{full_link}]({full_link})"
                markdown.append(f"| {app_name} | {markdown_link} | {status} | {last_modify} |\n")

            markdown.append("\n</details>\n\n")

    conn.close()

    with open(data_file, 'w') as f:
        f.writelines(markdown)

def renew_readme():
    template = ""
    with open(README_TEMPLATE_FILE, 'r') as f:
        template = f.read()

    def safe_read(path):
        try:
            with open(path, 'r') as fh:
                return fh.read()
        except Exception:
            return ""

    macos = safe_read(TABLE_MAP.get("macos"))
    ios = safe_read(TABLE_MAP.get("ios"))
    tvos = safe_read(TABLE_MAP.get("tvos"))
    ios_game = safe_read(TABLE_MAP.get("ios_game"))
    chinese = safe_read(TABLE_MAP.get("chinese"))
    signup = safe_read(TABLE_MAP.get("signup"))

    readme = template.replace("#{macos}", macos).replace("#{ios}", ios).replace("#{ios_game}", ios_game).replace("#{chinese}", chinese).replace("#{tvos}", tvos).replace("#{signup}", signup)
    with open("../README.md", 'w') as f:
        f.write(readme)

def main():
    testflight_link = sys.argv[1]
    table = sys.argv[2].lower()
    
    link_id_match = re.search(r"^https://testflight.apple.com/join/(.*)$", testflight_link, re.I)
    if link_id_match is not None:
        testflight_link = link_id_match.group(1)
    else:
        print(f"[Error] Invalid testflight_link. Exit...")
        exit(1)

    if table not in TABLE_MAP or table == "signup":
        print(f"[Error] Invalid table. Exit...")
        exit(1)

    # 从数据库删除
    conn = sqlite3.connect('../db/sqlite3.db')
    cur = conn.cursor()    
    sql = f"SELECT * FROM {table} WHERE testflight_link = '{testflight_link}';"
    res = cur.execute(sql)
    if len(list(res)) == 0:
        print(f"[warn] Data (https://testflight.apple.com/join/{testflight_link}) not found in table ({table}).")
        exit(0)
    
    sql = f"DELETE FROM {table} WHERE testflight_link = '{testflight_link}';"
    cur.execute(sql)
    conn.commit()
    print(f"[info] Deleted {conn.total_changes} row(s) into table: {table}")
    conn.close()

    renew_doc(TABLE_MAP[table], table)
    renew_readme()

if __name__ == "__main__":
    os.chdir(sys.path[0])
    
    main()