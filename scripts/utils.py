import json
import os
import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
LINKS_JSON = DATA_DIR / "links.json"
README_TEMPLATE_FILE = DATA_DIR / "README.template"
README_FILE = SCRIPT_DIR.parent / "README.md"

TABLE_MAP = {
    "macos": DATA_DIR / "macos.md",
    "ios": DATA_DIR / "ios.md",
    "tvos": DATA_DIR / "tvos.md",
    "ios_game": DATA_DIR / "ios_game.md",
    "chinese": DATA_DIR / "chinese.md",
    "signup": DATA_DIR / "signup.md"
}

TODAY = datetime.datetime.utcnow().date().strftime("%Y-%m-%d")

STATUS_INFO = {
    'Y': {'name': 'Available', 'description': 'Apps currently accepting new testers'},
    'F': {'name': 'Full', 'description': 'Apps that have reached their tester limit'},
    'N': {'name': 'No', 'description': 'Apps not currently accepting testers'},
    'D': {'name': 'Removed', 'description': 'Apps that have been removed from TestFlight'}
}

def load_links():
    if not LINKS_JSON.exists():
        return {k: {} for k in TABLE_MAP.keys() if k != "signup"}
    with open(LINKS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_links(links):
    with open(LINKS_JSON, 'w', encoding='utf-8') as f:
        json.dump(links, f, indent=2, ensure_ascii=False)

def renew_doc(table_name, links_data=None):
    data_file = TABLE_MAP.get(table_name)
    if not data_file:
        print(f"Error: Table {table_name} not found in TABLE_MAP")
        return

    # Read title from existing file (first line)
    title = ""
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            title = f.readline().strip()
    except Exception:
        title = data_file.name

    if links_data is None:
        links_data = load_links()
    
    table_data = links_data.get(table_name, {})
    
    markdown = [f"{title}\n\n"]

    for status_code in ['Y', 'F', 'N', 'D']:
        status_data = STATUS_INFO[status_code]
        
        # Filter and sort apps by name
        apps = []
        for link, info in table_data.items():
            if info['status'] == status_code:
                apps.append({
                    'app_name': info['app_name'],
                    'testflight_link': link,
                    'status': info['status'],
                    'last_modify': info['last_modify']
                })
        
        apps.sort(key=lambda x: x['app_name'].lower())

        if apps:
            app_count = len(apps)
            if status_code == 'Y':
                markdown.append(f"<details open>\n")
            else:
                markdown.append(f"<details>\n")
            
            markdown.append(f"<summary><strong>{status_data['name']} ({app_count} app{'s' if app_count != 1 else ''})</strong> - {status_data['description']}</summary>\n\n")

            if status_code == 'Y':
                markdown.append(f"_✅ These {app_count} apps are currently accepting new testers! Click the links to join._\n\n")
            elif status_code == 'F':
                markdown.append(f"_⚠️ These {app_count} apps have reached their tester limit. Try checking back later._\n\n")

            markdown.append("| Name | TestFlight Link | Status | Last Updated |\n")
            markdown.append("| --- | --- | --- | --- |\n")

            for app in apps:
                full_link = f"https://testflight.apple.com/join/{app['testflight_link']}"
                markdown_link = f"[{full_link}]({full_link})"
                markdown.append(f"| {app['app_name']} | {markdown_link} | {app['status']} | {app['last_modify']} |\n")

            markdown.append("\n</details>\n\n")

    with open(data_file, 'w', encoding='utf-8') as f:
        f.writelines(markdown)

def renew_readme():
    if not README_TEMPLATE_FILE.exists():
        print(f"Error: Template file {README_TEMPLATE_FILE} not found")
        return

    with open(README_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()

    def safe_read(path):
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                return fh.read()
        except Exception:
            return ""

    content = template
    for key, path in TABLE_MAP.items():
        placeholder = f"#{{{key}}}"
        content = content.replace(placeholder, safe_read(path))

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
