#!/usr/bin/python
'''
Author       : tom-snow
Date         : 2022-03-16 19:32:32
LastEditTime : 2025-11-04 11:28:05
LastEditors  : pluwen
Description  : 
FilePath     : /awesome-testflight-link/scripts/add_link.py
'''

import sqlite3
import asyncio
import aiohttp
import re, os, sys, datetime, random

BASE_URL = "https://testflight.apple.com/"

TABLE_MAP = {
    "macos": "./data/macos.md",
    "ios": "./data/ios.md",
    "tvos": "./data/tvos.md",
    "ios_game": "./data/ios_game.md",
    "chinese": "./data/chinese.md",
    "signup": "./data/signup.md"
}
README_TEMPLATE_FILE = "./data/README.template"
TODAY = datetime.datetime.utcnow().date().strftime("%Y-%m-%d")

FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")
# 除了不接受新测试员外，其他的（已满/可加入）可以得到应用名
APP_NAME_PATTERN = re.compile(r"Join the (.+) beta - TestFlight - Apple")
APP_NAME_CH_PATTERN = re.compile(r"加入 Beta 版“(.+)” - TestFlight - Apple")

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
            # 默认展开 Available 部分，其余状态保持收起
            if status_code == 'Y':
                markdown.append(f"<details open>\n")
            else:
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

    # use exact placeholder replacement to match README.template
    readme = template.replace("#{macos}", macos).replace("#{ios}", ios).replace("#{ios_game}", ios_game).replace("#{chinese}", chinese).replace("#{tvos}", tvos).replace("#{signup}", signup)
    with open("../README.md", 'w') as f:
        f.write(readme)

async def check_status(session, key, retry=10):
    status = 'N'
    app_name = "None"
    for i in range(retry):
        try:
            async with session.get(f'/join/{key}') as resp:
                resp.raise_for_status()
                resp_html = await resp.text()
                if NO_PATTERN.search(resp_html) is not None:
                    status = 'N'
                elif FULL_PATTERN.search(resp_html) is not None:
                    status = 'F'
                else:
                    status = 'Y'
                app_name_search = APP_NAME_PATTERN.search(resp_html)
                app_name_ch_search = APP_NAME_CH_PATTERN.search(resp_html)
                if app_name_search is not None:
                    app_name = app_name_search.group(1)
                elif app_name_ch_search is not None:
                    app_name = app_name_ch_search.group(1)
                return (key, status, app_name)
        except aiohttp.ClientResponseError as e:
            if resp.status == 404:
                return (key, 'D', app_name)
            rand = round(random.random(), 3)
            print(f"[warn] {e}, wait {i*(rand+1)+1} s. Retry({i}/{retry})")
            await asyncio.sleep(i*(rand+1)+1)
    print(f"[warn] Key ({key}) have max retries, return default value!")
    return (key, status, app_name)

async def main():
    testflight_link = sys.argv[1]
    table = sys.argv[2].lower()
    app_name = sys.argv[3]
    last_modify = TODAY
    
    link_id_match = re.search(r"^https://testflight.apple.com/join/(.*)$", testflight_link, re.I)
    if link_id_match is not None:
        testflight_link = link_id_match.group(1)
    else:
        print(f"[Error] Invalid testflight_link. Exit...")
        exit(1)

    if table not in TABLE_MAP or table == "signup":
        print(f"[Error] Invalid table. Exit...")
        exit(1)

    if app_name is None or app_name == "":
        app_name = "None"
    
    # 稳妥起见限制同时 5 个同 host 的请求
    conn = aiohttp.TCPConnector(limit=10, limit_per_host=5)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2357.130 Safari/537.36 qblink wegame.exe QBCore/3.70.66.400 QQBrowser/9.0.2524.400"
    }
    async with aiohttp.ClientSession(BASE_URL, connector=conn, headers=headers) as session:
        coroutines_list = []
        coroutines_list.append(check_status(session, testflight_link))
        result = await asyncio.gather(*coroutines_list)
        for row in result:
            if app_name.capitalize() == "None":
                app_name = row[2]
            status = row[1]

    # 插入数据库
    conn = sqlite3.connect('../db/sqlite3.db')
    cur = conn.cursor()    
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
    print(f"[info] Writed {conn.total_changes} row(s) into table: {table}")
    conn.close()

    renew_doc(TABLE_MAP[table], table)
    renew_readme()

if __name__ == "__main__":
    os.chdir(sys.path[0])
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
