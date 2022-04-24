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
    "ios_game": "./data/ios_game.md",
    "chinese": "./data/chinese.md",
    "signup": "./data/signup.md"
}
README_TEMPLATE_FILE = "./data/README.template"


def renew_doc(data_file, table):
    # header
    markdown = []
    with open(data_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            columns = [ column.strip() for column in line.split("|") ]
            markdown.append(line)
            if len(columns) > 2 and re.match(r"^:?-+:?$", columns[1]):
                break
    # 
    conn = sqlite3.connect('../db/sqlite3.db')
    cur = conn.cursor()
    res = cur.execute(f"SELECT app_name, testflight_link, status, last_modify FROM {table} ORDER BY app_name;")
    for row in res:
        app_name, testflight_link, status, last_modify = row
        testflight_link = f"[https://testflight.apple.com/join/{testflight_link}](https://testflight.apple.com/join/{testflight_link})"
        markdown.append(f"| {app_name} | {testflight_link} | {status} | {last_modify} |\n")
    conn.close()
    # 
    with open(data_file, 'w') as f:
        lines = f.writelines(markdown)

def renew_readme():
    template = ""
    with open(README_TEMPLATE_FILE, 'r') as f:
        template = f.read()
    macos = ""
    with open(TABLE_MAP["macos"], 'r') as f:
        macos = f.read()
    ios = ""
    with open(TABLE_MAP["ios"], 'r') as f:
        ios = f.read()
    ios_game = ""
    with open(TABLE_MAP["ios_game"], 'r') as f:
        ios_game = f.read()
    chinese = ""
    with open(TABLE_MAP["chinese"], 'r') as f:
        chinese = f.read()
    signup = ""
    with open(TABLE_MAP["signup"], 'r') as f:
        signup = f.read()
    readme = template.format(macos=macos, ios=ios, ios_game=ios_game, chinese=chinese, signup=signup)
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