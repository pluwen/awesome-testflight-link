#!/usr/bin/python
'''
Author       : tom-snow
Date         : 2022-03-14 19:56:48
LastEditTime : 2025-11-04 11:28:05
LastEditors  : pluwen
Description  : 将 markdown 表格中的数据导入 sqlite3 （正常情况下你不需要运行此脚本，因为我已经建立好数据库了）
FilePath     : /awesome-testflight-link/scripts/init_database.py
'''

import sqlite3
import datetime, re, os, sys

TABLE_MAP = {
    "macos": "./data/macos.md",
    "ios": "./data/ios.md",
    "tvos": "./data/tvos.md",
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

    # ensure table exists (basic schema); this makes the script idempotent
    try:
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
          app_name TEXT,
          testflight_link TEXT NOT NULL,
          status TEXT,
          last_modify TEXT,
          PRIMARY KEY (testflight_link)
        );
        """)
    except Exception:
        pass

    with open(data_file, 'r') as f:
        lines = f.readlines()
        data_flag = False # 是否到真正的数据区域了
        for line in lines:
            # Basic guard: skip empty lines
            if not line.strip():
                continue

            columns = [ column.strip() for column in line.split("|") ]
            if not data_flag:
                # detect the markdown table separator like | --- | --- |
                if len(columns) > 2 and re.match(r"^:?-+:?$", columns[1]):
                    data_flag = True
                continue

            # 开始处理数据
            # Ensure we have at least 3 columns (leading/trailing pipes create empty entries)
            if len(columns) < 4:
                # malformed row, record and skip
                print(f"[Warn] Malformed table row (skipped): {line.strip()}")
                INVALID_DATA.append(line)
                continue

            try:
                _, app_name, testflight_link = columns[:3]
            except ValueError:
                print(f"[Warn] Could not parse row (skipped): {line.strip()}")
                INVALID_DATA.append(line)
                continue

            status, last_modify = columns[3:5] if len(columns) > 4 else ["", ""]
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
                # Duplicate primary key or other integrity issue; log and continue
                print(f"[sqlite3.IntegrityError] {e} -- Table: {table}; Data: {data}")
                continue
            except Exception as e:
                raise e
    
    conn.commit()
    print(f"[info] Writed {conn.total_changes} rows into table: {table}")

    conn.close()

def other_links():
    # For signup, do not write into database per user request.
    # Append INVALID_DATA lines into ./data/signup.md if they are not already present.
    try:
        with open('./data/signup.md', 'r') as f:
            exists = f.read().splitlines()
    except FileNotFoundError:
        exists = []

    new_lines = 0
    if INVALID_DATA:
        with open('./data/signup.md', 'a') as f:
            for l in INVALID_DATA:
                # Trim newline for comparison
                if l.strip() not in [e.strip() for e in exists]:
                    f.write(l)
                    new_lines += 1

    if new_lines:
        print(f"[info] Appended {new_lines} lines to ./data/signup.md for review")

def main():
    for table in TABLE_MAP:
        process(TABLE_MAP[table], table)

    other_links()


if __name__ == "__main__":
    os.chdir(sys.path[0])
    
    main()

    print(f"[info] All Done!")