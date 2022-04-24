#!/usr/bin/python
'''
Author       : tom-snow
Date         : 2022-03-14 19:56:48
LastEditTime : 2022-03-17 13:36:08
LastEditors  : tom-snow
Description  : 将 markdown 表格中的数据导入 sqlite3 （正常情况下你不需要运行此脚本，因为我已经建立好数据库了）
FilePath     : /awesome-testflight-link/scripts/init_database.py
'''

import sqlite3
import datetime, re, os, sys

TABLE_MAP = {
    "macos": "./data/macos.md",
    "ios": "./data/ios.md",
    "ios_game": "./data/ios_game.md",
    "chinese": "./data/chinese.md"
}
"""
// 请自行建立数据库表
CREATE TABLE "macos" (
  "app_name" TEXT,
  "testflight_link" TEXT NOT NULL,
  "status" TEXT,
  "last_modify" TEXT,
  PRIMARY KEY ("testflight_link")
);
"""
INVALID_DATA = []
TODAY = datetime.datetime.utcnow().date().strftime("%Y-%m-%d")

def process(data_file, table):
    conn = sqlite3.connect('../db/sqlite3.db')
    cur = conn.cursor()

    with open(data_file, 'r') as f:
        lines = f.readlines()
        data_flag = False # 是否到真正的数据区域了
        for line in lines:
            columns = [ column.strip() for column in line.split("|") ]
            if not data_flag:
                if len(columns) > 2 and re.match(r"^:?-+:?$", columns[1]):
                    data_flag = True
                continue
            # 开始处理数据
            # 
            _, app_name, testflight_link = columns[:3]
            status, last_modify = columns[3:5] if len(columns)>4 else [""] * 2
            link_id_match = re.search(r"\]\(https://testflight.apple.com/join/(.*)\)", testflight_link, re.I)
            if link_id_match is not None:
                testflight_link = link_id_match.group(1)
            else:
                print(f"[Warn] Invalid testflight_link, record(will be save into ./data/sign_up.md): \n\t\"{columns}\"")
                INVALID_DATA.append(line)
                continue
            if status is None or status == "":
                status = "N"
            if last_modify is None or last_modify == "":
                last_modify = TODAY
            # 插入数据库
            sql = f"INSERT INTO {table} (app_name, testflight_link, status, last_modify) VALUES(?, ?, ?, ?);"
            data = (app_name, testflight_link, status, last_modify)
            try:
                cur.execute(sql, data)
            except sqlite3.IntegrityError as e:
                print(f"[sqlite3.IntegrityError - 1] {e}")
                print(f"[sqlite3.IntegrityError - 2] Table: {table}; Data: {data}")
            except Exception as e:
                raise e
    
    conn.commit()
    print(f"[info] Writed {conn.total_changes} rows into table: {table}")

    conn.close()

def other_links():
    with open('./data/signup.md', 'r+') as f:
        exists_data = f.readlines()
        temp = []
        for line in INVALID_DATA:
            if line not in exists_data:
                temp.append(line)
        f.writelines(temp)
        if len(temp):
            print(f"[info] Write {len(temp)} raws to ./data/signup.md")

def main():
    for table in TABLE_MAP:
        process(TABLE_MAP[table], table)

    other_links()


if __name__ == "__main__":
    os.chdir(sys.path[0])
    
    main()

    print(f"[info] All Done!")