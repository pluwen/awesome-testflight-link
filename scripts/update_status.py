#!/usr/bin/python
'''
Author       : tom-snow
Date         : 2022-03-15 13:47:49
LastEditTime : 2022-03-16 15:37:53
LastEditors  : tom-snow
Description  : 
FilePath     : /awesome-testflight-link/scripts/update_status.py
'''

import sqlite3
import asyncio
import aiohttp
import re, os, sys, time
import requests

BASE_URL = "https://testflight.apple.com/"

FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")
# 除了不接受新测试员外，其他的（已满/可加入）可以得到应用名
APP_NAME_PATTERN = re.compile(r"Join the (.+) beta - TestFlight - Apple")
APP_NAME_CH_PATTERN = re.compile(r"加入 Beta 版“(.+)” - TestFlight - Apple")

def get_tf_link_keys(table):
    conn = sqlite3.connect('../db/sqlite3.db')
    cur = conn.cursor()
    res = cur.execute(f"SELECT testflight_link from {table}")
    return map(lambda x:x[0], res)

async def check_status(session, key):
    status = 'N'
    async with session.get(f'/join/{key}') as resp:
        if (resp.status == 200):
            resp_html = await resp.text()
            if NO_PATTERN.search(resp_html) is not None:
                status = 'N'
            elif FULL_PATTERN.search(resp_html) is not None:
                status = 'F'
            else:
                status = 'Y'
            return (key, status)
            

async def main():
    start = time.time()
    
    async with aiohttp.ClientSession(BASE_URL) as session:
        link_keys =  [*get_tf_link_keys("macos")]
        coroutines_list = []
        for key in link_keys:
            coroutines_list.append(check_status(session, key))
        result = await asyncio.gather(*coroutines_list)
        print(result)
            
    print(time.time() - start)

def normal():
    start = time.time()
    link_keys =  [*get_tf_link_keys("macos")]
    
    for key in link_keys:
        resp_html = requests.get(f"{BASE_URL}/join/{key}").text
        if NO_PATTERN.search(resp_html) is not None:
            status = 'N'
        elif FULL_PATTERN.search(resp_html) is not None:
            status = 'F'
        else:
            status = 'Y'
        print(key, status)

    print(time.time() - start)

if __name__ == "__main__":
    os.chdir(sys.path[0])
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    normal()

    print(f"[info] All Done!")
