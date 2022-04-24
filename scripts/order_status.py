#!/usr/bin/python
'''
Author       : tom-snow
Date         : 2022-03-17 11:32:32
LastEditTime : 2022-03-17 12:17:34
LastEditors  : tom-snow
Description  : 
FilePath     : /awesome-testflight-link/scripts/order_status.py
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
    res = cur.execute(f"""SELECT app_name, testflight_link, status, last_modify FROM {table} ORDER BY 
        CASE status
            WHEN 'Y' THEN 0
            WHEN 'F' THEN 1
            WHEN 'N' THEN 2
            WHEN 'D' THEN 3
        END;""")
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
    for table in TABLE_MAP:
        if table == "signup": # 数据库没有此表
            continue

        renew_doc(TABLE_MAP[table], table)
        renew_readme()

if __name__ == "__main__":
    os.chdir(sys.path[0])
    
    main()