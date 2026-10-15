import asyncio
import os
from playwright.async_api import async_playwright

async def test_cctv():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1600, "height": 980})
        
        file_path = os.path.abspath("public/index.html")
        await page.goto(f"file:///{file_path.replace(os.sep, '/')}")
        await page.wait_for_timeout(1000)
        
        # Click CCTV tab
        await page.click("#tab-btn-cctv")
        await page.wait_for_timeout(3000)
        
        cctv_screenshot = "public/assets/logos/renovated_cctv.png"
        artifact_cctv = r"C:\Users\hp\.gemini\antigravity\brain\99aa7469-6c3c-4636-ae9e-1781c68925c2\renovated_cctv.png"
        await page.screenshot(path=cctv_screenshot)
        await page.screenshot(path=artifact_cctv)
        print("Captured CCTV screenshot successfully at", artifact_cctv)
        
        await browser.close()

asyncio.run(test_cctv())
