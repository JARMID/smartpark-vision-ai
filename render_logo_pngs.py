import asyncio
import os
import shutil
from playwright.async_api import async_playwright

artifact_dir = r"C:\Users\hp\.gemini\antigravity\brain\99aa7469-6c3c-4636-ae9e-1781c68925c2"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 512, 'height': 512}, device_scale_factor=2)
        page = await context.new_page()

        for i in range(1, 11):
            svg_file = os.path.abspath(f"public/assets/logos/logo_{i}.svg")
            png_file = os.path.abspath(f"public/assets/logos/logo_{i}.png")
            artifact_png = os.path.join(artifact_dir, f"logo_{i}.png")
            
            # Load SVG directly in browser
            uri = "file:///" + svg_file.replace("\\", "/")
            await page.goto(uri)
            await page.screenshot(path=png_file)
            shutil.copy2(png_file, artifact_png)
            print(f"Rendered logo_{i}.png successfully")

        # Also render the entire showcase gallery
        showcase_file = os.path.abspath("public/assets/logos/showcase.html")
        showcase_page = await browser.new_page(viewport={'width': 1400, 'height': 1100})
        await showcase_page.goto("file:///" + showcase_file.replace("\\", "/"))
        await asyncio.sleep(0.5)
        showcase_png = os.path.abspath("public/assets/logos/showcase.png")
        await showcase_page.screenshot(path=showcase_png, full_page=True)
        shutil.copy2(showcase_png, os.path.join(artifact_dir, "showcase.png"))
        print("Rendered showcase.png successfully")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
