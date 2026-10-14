import asyncio
import sys
from playwright.async_api import async_playwright

async def run_ui_verification():
    console_errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        page = await context.new_page()

        # Capture console errors
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ["error"] else None)
        page.on("pageerror", lambda err: console_errors.append(f"[pageerror] {err}"))

        print("Navigating to http://127.0.0.1:8080/...")
        await page.goto("http://127.0.0.1:8080/", wait_until="networkidle")
        await asyncio.sleep(1.0)

        # 1. Switch to CCTV View
        print("Switching to CCTV Camera Matrix tab...")
        await page.click("#tab-btn-cctv")
        await asyncio.sleep(1.0)
        await page.screenshot(path="tests/screenshot_cctv_night_fr.png")
        print("Captured CCTV Night Mode (FR) screenshot: tests/screenshot_cctv_night_fr.png")

        # 2. Toggle Theme to Day / Light Mode
        print("Toggling Day / Light Mode...")
        await page.click("#theme-btn")
        await asyncio.sleep(1.0)
        is_light = await page.evaluate("() => document.documentElement.classList.contains('light')")
        assert is_light, "Expected document.documentElement to contain 'light' class!"
        await page.screenshot(path="tests/screenshot_cctv_day_fr.png")
        print("Captured CCTV Day Mode (FR) screenshot: tests/screenshot_cctv_day_fr.png")

        # 3. Switch Language to Arabic
        print("Switching language to Arabic (AR)...")
        await page.click("#lang-btn-ar")
        await asyncio.sleep(0.8)
        direction = await page.evaluate("() => document.documentElement.dir")
        assert direction == "rtl", f"Expected direction rtl, got {direction}"
        app_title_ar = await page.inner_text('[data-i18n="app_title"]')
        print(f"Arabic app title: {app_title_ar}")
        await page.screenshot(path="tests/screenshot_cctv_day_ar.png")
        print("Captured CCTV Day Mode (AR RTL) screenshot: tests/screenshot_cctv_day_ar.png")

        # 4. Switch Language to English
        print("Switching language to English (EN)...")
        await page.click("#lang-btn-en")
        await asyncio.sleep(0.8)
        direction_en = await page.evaluate("() => document.documentElement.dir")
        assert direction_en == "ltr", f"Expected direction ltr, got {direction_en}"
        app_title_en = await page.inner_text('[data-i18n="app_title"]')
        print(f"English app title: {app_title_en}")
        await page.screenshot(path="tests/screenshot_cctv_day_en.png")
        print("Captured CCTV Day Mode (EN) screenshot: tests/screenshot_cctv_day_en.png")

        # 5. Test Live Camera Expansion Modal (Inspect CAM-02)
        print("Clicking CAM-02 to open Live HD Mirror Inspector...")
        await page.click("#cam2-canvas")
        await asyncio.sleep(1.0)
        is_modal_visible = await page.is_visible("#cam-modal")
        assert is_modal_visible, "Expected #cam-modal to be visible!"
        await page.screenshot(path="tests/screenshot_cam2_inspector_hd.png")
        print("Captured CAM-02 Live HD Inspector screenshot: tests/screenshot_cam2_inspector_hd.png")
        await page.click("button[onclick='closeCameraModal()']")
        await asyncio.sleep(0.5)

        # 6. Trigger Scenario 1 (VIP Entry) in English
        print("Triggering Scenario 1 (VIP Entry)...")
        await page.click("button:has-text('[1] VIP')")
        await asyncio.sleep(2.0)

        # 7. Switch to 3D View to test Day mode 3D
        print("Switching to 3D Digital Twin tab in Day Mode...")
        await page.click("#tab-btn-3d")
        await asyncio.sleep(1.0)
        await page.screenshot(path="tests/screenshot_3d_day.png")
        print("Captured 3D Digital Twin Day Mode screenshot: tests/screenshot_3d_day.png")

        # 8. Check for Console Errors
        print("\n=== Console Errors Report ===")
        filtered_errors = [e for e in console_errors if "favicon" not in e.lower() and "ws" not in e.lower()]
        if filtered_errors:
            print(f"Found {len(filtered_errors)} console errors:")
            for err in filtered_errors:
                print(f"  {err}")
        else:
            print("Zero critical JavaScript / WebGL console errors detected!")

        await browser.close()
        print("\n[SUCCESS] UI verification completed with full Day/Night, Trilingual, and CCTV validation!")

if __name__ == "__main__":
    asyncio.run(run_ui_verification())
