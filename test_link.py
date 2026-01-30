#!/usr/bin/env python3
import asyncio
import aiohttp
import sys
sys.path.insert(0, '/Users/pluwen/Documents/Code/awesome-testflight-link/scripts')
from platform_detector import detect_platforms

async def test_link(link_key):
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    try:
        connector = aiohttp.TCPConnector(limit=5, limit_per_host=2)
        async with aiohttp.ClientSession(base_url="https://testflight.apple.com/", connector=connector) as session:
            async with session.get(f'/join/{link_key}', headers={'User-Agent': ua}) as resp:
                if resp.status == 404:
                    print(f"❌ 链接已删除 (404)")
                    return
                
                resp.raise_for_status()
                html = await resp.text()
                
                # 检测平台
                platforms = detect_platforms(html)
                
                print(f"✅ 链接状态: 有效")
                print(f"🔍 检测到的平台: {sorted(list(platforms)) if platforms else '（未检测到）'}")
                print(f"\n📝 完整链接: https://testflight.apple.com/join/{link_key}")
                
                # 显示一些 HTML 信息
                if "This beta is full" in html or "版本的测试员已满" in html:
                    print("⚠️ 状态: 测试员已满")
                elif "This beta isn't accepting any new testers" in html or "版本目前不接受任何新测试员" in html:
                    print("⚠️ 状态: 不接受新测试员")
                elif "TestFlight" in html:
                    print("✅ 状态: 可加入")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    link_key = "NXLBigzY"
    asyncio.run(test_link(link_key))
