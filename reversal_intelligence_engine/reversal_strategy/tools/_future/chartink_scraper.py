"""
tools/_future/chartink_scraper.py

Automates CSV download from the Chartink screener dashboard
using Playwright browser automation.

Not currently wired into the pipeline. Intended for future
integration with IngestNode or a dedicated IngestionTool.
"""

# Guard prevents accidental execution on import
if __name__ == "__main__":
    from playwright.sync_api import sync_playwright

    URL = "https://chartink.com/dashboard/34179"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page    = browser.new_page()

        page.goto(URL, wait_until="networkidle")

        page.get_by_text(
            'CCI Weekly crossing above -100 (Trendline reversal scanner)'
        ).is_visible()

        csv_buttons = page.locator('//span[text()="CSV"]')
        total = csv_buttons.count()

        for i in range(total):
            csv_buttons.nth(i).click()
            page.wait_for_timeout(1000)

        input("Browser is open. Press Enter to close ...")
        browser.close()
