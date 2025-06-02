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
    # Get the title from the original file
    title = ""
    with open(data_file, 'r') as f:
        title = f.readline().strip()
    
    # Connect to database and get apps by status
    conn = sqlite3.connect('../db/sqlite3.db')
    cur = conn.cursor()
    
    # Define status categories and their descriptions
    status_info = {
        'Y': {'name': 'Available', 'description': 'Apps currently accepting new testers'},
        'F': {'name': 'Full', 'description': 'Apps that have reached their tester limit'},
        'N': {'name': 'No', 'description': 'Apps not currently accepting testers'},
        'D': {'name': 'Removed', 'description': 'Apps that have been removed from TestFlight'}
    }
    
    markdown = [f"{title}\n\n"]
    
    # Generate sections for each status
    for status_code in ['Y', 'F', 'N', 'D']:
        status_data = status_info[status_code]
        
        # Get apps with this status
        res = cur.execute(f"""SELECT app_name, testflight_link, status, last_modify FROM {table} 
                             WHERE status = ? ORDER BY app_name""", (status_code,))
        apps = res.fetchall()
        
        if apps:  # Only create section if there are apps with this status
            # Create collapsible section with enhanced formatting
            app_count = len(apps)
            markdown.append(f"<details>\n")
            markdown.append(f"<summary><strong>{status_data['name']} ({app_count} app{'s' if app_count != 1 else ''})</strong> - {status_data['description']}</summary>\n\n")
            
            # Add helpful note for Available apps
            if status_code == 'Y' and app_count > 0:
                markdown.append(f"_✅ These {app_count} apps are currently accepting new testers! Click the links to join._\n\n")
            elif status_code == 'F' and app_count > 0:
                markdown.append(f"_⚠️ These {app_count} apps have reached their tester limit. Try checking back later._\n\n")
            
            # Add table header
            markdown.append("| Name | TestFlight Link | Status | Last Updated |\n")
            markdown.append("| --- | --- | --- | --- |\n")
            
            # Add apps to table
            for app_name, testflight_link, status, last_modify in apps:
                full_link = f"https://testflight.apple.com/join/{testflight_link}"
                markdown_link = f"[{full_link}]({full_link})"
                markdown.append(f"| {app_name} | {markdown_link} | {status} | {last_modify} |\n")
            
            markdown.append("\n</details>\n\n")
    
    conn.close()
    
    # Write the new markdown
    with open(data_file, 'w') as f:
        f.writelines(markdown)

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
    readme = template.replace("#{macos}", macos).replace("#{ios}", ios).replace("#{ios_game}", ios_game).replace("#{chinese}", chinese).replace("#{signup}", signup)
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