import asyncio
import os
from playwright.async_api import async_playwright

async def test_ui():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1600, "height": 980})
        
        file_path = os.path.abspath("public/index.html")
        await page.goto(f"file:///{file_path.replace(os.sep, '/')}")
        await page.wait_for_timeout(2500)
        
        screenshot_path = "public/assets/logos/renovated_dashboard.png"
        artifact_path = r"C:\Users\hp\.gemini\antigravity\brain\99aa7469-6c3c-4636-ae9e-1781c68925c2\renovated_dashboard.png"
        
        await page.screenshot(path=screenshot_path)
        await page.screenshot(path=artifact_path)
        print("Captured screenshot successfully at", artifact_path)
        
        await browser.close()

asyncio.run(test_ui())
