import json
import datetime
import asyncio
import re
from pathlib import Path

import aiohttp

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
LINKS_JSON = DATA_DIR / "links.json"
README_TEMPLATE_FILE = DATA_DIR / "README.template"
README_FILE = SCRIPT_DIR.parent / "README.md"

TODAY = datetime.datetime.utcnow().date().strftime("%Y-%m-%d")
BASE_URL = "https://testflight.apple.com/"
TESTFLIGHT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

FULL_PATTERN = re.compile(r"版本的测试员已满|This beta is full")
NO_PATTERN = re.compile(r"版本目前不接受任何新测试员|This beta isn't accepting any new testers right now")
APP_NAME_PATTERN = re.compile(r"Join the (.+) beta - TestFlight - Apple")
APP_NAME_CH_PATTERN = re.compile(r'加入 Beta 版"(.+)" - TestFlight - Apple')
MISSING_NAMES = {"", "None", "none", "Unknown"}
VALID_PLATFORMS = {'ios', 'ipados', 'macos', 'tvos', 'visionos'}

STATUS_INFO = {
    'Y': {'name': 'Available', 'description': 'Apps currently accepting new testers'},
    'F': {'name': 'Full', 'description': 'Apps that have reached their tester limit'},
    'N': {'name': 'No', 'description': 'Apps not currently accepting testers'},
    'D': {'name': 'Removed', 'description': 'Apps that have been removed from TestFlight'}
}

def load_links():
    with open(LINKS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_links(links):
    with open(LINKS_JSON, 'w', encoding='utf-8') as f:
        json.dump(links, f, indent=2, ensure_ascii=False)


def parse_platforms_from_string(s: str) -> list:
    """Parse comma-separated platform string into validated list."""
    if not s:
        return []
    parts = [p.strip().lower() for p in s.split(',') if p.strip()]
    return [p for p in parts if p in VALID_PLATFORMS]


def extract_app_name(html: str) -> str:
    app_name_search = APP_NAME_PATTERN.search(html)
    app_name_ch_search = APP_NAME_CH_PATTERN.search(html)
    if app_name_search:
        return app_name_search.group(1)
    if app_name_ch_search:
        return app_name_ch_search.group(1)
    return ""


def detect_testflight_status(html: str, fallback_status: str = 'N') -> str:
    if NO_PATTERN.search(html):
        return 'N'
    if FULL_PATTERN.search(html):
        return 'F'
    if "TestFlight" in html:
        return 'Y'
    return fallback_status


async def check_testflight_status(
    session,
    key,
    current_status='N',
    app_name=None,
    retry=5,
    include_html=False,
):
    """Fetch TestFlight status and app name for a join code."""
    resolved_name = app_name or ""

    for i in range(retry):
        try:
            async with session.get(
                f'/join/{key}',
                headers={'User-Agent': TESTFLIGHT_USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 404:
                    result = (key, 'D', resolved_name)
                    return (*result, "") if include_html else result

                resp.raise_for_status()
                html_content = await resp.text()
                status = detect_testflight_status(html_content, current_status)
                fetched_name = extract_app_name(html_content)

                if (not resolved_name or resolved_name in MISSING_NAMES) and fetched_name:
                    resolved_name = fetched_name

                result = (key, status, resolved_name)
                return (*result, html_content) if include_html else result
        except asyncio.TimeoutError:
            error_name = "Timeout"
        except Exception as e:
            error_name = type(e).__name__

        if i < retry - 1:
            wait_time = 2 ** i
            print(f"[warn] {key} - {error_name}, waiting {wait_time}s before retry ({i+1}/{retry})")
            await asyncio.sleep(wait_time)

    print(f"[warn] {key} - Failed after {retry} retries, using default values")
    result = (key, current_status, resolved_name)
    return (*result, "") if include_html else result


def escape_markdown_table_cell(value) -> str:
    text = str(value).replace("\r\n", "<br>").replace("\n", "<br>").replace("\r", "<br>")
    return text.replace("|", r"\|")


def generate_platform_section(table_name, links_data):
    """从 links.json 直接生成平台部分的 markdown 内容"""
    all_links = links_data.get("_links", {})
    
    # 获取该平台的所有应用
    table_links = {
        link_id: info for link_id, info in all_links.items()
        if table_name in info.get("tables", [])
    }
    
    if not table_links:
        return ""
    
    markdown = []
    
    for status_code in ['Y', 'F', 'N', 'D']:
        # 按状态过滤和排序应用
        apps = sorted(
            [
                {
                    'app_name': info['app_name'],
                    'testflight_link': link_id,
                    'status': info['status'],
                    'last_modify': info['last_modify']
                }
                for link_id, info in table_links.items()
                if info['status'] == status_code
            ],
            key=lambda x: x['app_name'].lower()
        )
        
        if not apps:
            continue
        
        status_data = STATUS_INFO[status_code]
        app_count = len(apps)
        
        # 生成分类
        markdown.append(f"<details {'open' if status_code == 'Y' else ''}>\n")
        markdown.append(f"<summary><strong>{status_data['name']} ({app_count} app{'s' if app_count != 1 else ''})</strong> - {status_data['description']}</summary>\n\n")
        
        if status_code == 'Y':
            markdown.append(f"_✅ These {app_count} apps are currently accepting new testers! Click the links to join._\n\n")
        elif status_code == 'F':
            markdown.append(f"_⚠️ These {app_count} apps have reached their tester limit. Try checking back later._\n\n")
        
        markdown.append("| Name | TestFlight Link | Status | Last Updated |\n")
        markdown.append("| --- | --- | --- | --- |\n")
        
        for app in apps:
            full_link = f"https://testflight.apple.com/join/{app['testflight_link']}"
            app_name = escape_markdown_table_cell(app['app_name'])
            status = escape_markdown_table_cell(app['status'])
            last_modify = escape_markdown_table_cell(app['last_modify'])
            markdown.append(f"| {app_name} | [{full_link}]({full_link}) | {status} | {last_modify} |\n")
        
        markdown.append("\n</details>\n\n")

    return "".join(markdown)

def renew_readme():
    if not README_TEMPLATE_FILE.exists():
        print(f"Error: Template file {README_TEMPLATE_FILE} not found")
        return

    links_data = load_links()
    
    with open(README_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()

    content = template
    
    # 从 links.json 生成平台内容
    platform_map = {
        "iOS_APPS": ("ios", "## iOS App List\n\n"),
        "iPadOS_APPS": ("ipados", "## iPadOS App List\n\n"),
        "macOS_APPS": ("macos", "## macOS App List\n\n"),
        "tvOS_APPS": ("tvos", "## tvOS App List\n\n"),
        "visionOS_APPS": ("visionos", "## visionOS App List\n\n"),
    }
    
    for placeholder, (table_name, heading) in platform_map.items():
        platform_content = generate_platform_section(table_name, links_data)
        # 只在有内容时才包含标题
        if platform_content.strip():
            content = content.replace(f"#{{{placeholder}}}", heading + platform_content)
        else:
            # 如果没有内容，只删除占位符
            content = content.replace(f"#{{{placeholder}}}", "")
    
    # 读取并插入 signup.md 文件内容
    signup_file = DATA_DIR / "signup.md"
    if signup_file.exists():
        try:
            with open(signup_file, 'r', encoding='utf-8') as f:
                signup_content = f.read()
            # 从第一个 # 开始提取内容（跳过文件头注释）
            content = content.replace("#{SIGNUP_APPS}", signup_content)
        except Exception as e:
            print(f"[warn] Failed to read signup.md: {e}")
            content = content.replace("#{SIGNUP_APPS}", "")
    else:
        content = content.replace("#{SIGNUP_APPS}", "")

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
