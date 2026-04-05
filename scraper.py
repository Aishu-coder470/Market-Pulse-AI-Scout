"""
Competitor Intelligence Scraper Agent
Uses Playwright to scrape competitor websites autonomously
"""

import asyncio
import json
import re
import os
from datetime import datetime, timezone
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


COMPETITORS = [
    {
        "name": "Notion",
        "url": "https://www.notion.so/pricing",
        "selectors": {
            "pricing_section": "main",
            "page_title": "title"
        }
    },
    {
        "name": "Linear",
        "url": "https://linear.app/pricing",
        "selectors": {
            "pricing_section": "main",
            "page_title": "title"
        }
    },
    {
        "name": "Vercel",
        "url": "https://vercel.com/pricing",
        "selectors": {
            "pricing_section": "main",
            "page_title": "title"
        }
    }
]


async def scrape_page(playwright, competitor: dict) -> dict:
    """Scrape a single competitor page using Playwright"""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    page = await context.new_page()

    result = {
        "name": competitor["name"],
        "url": competitor["url"],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "raw_text": "",
        "prices": [],
        "features": [],
        "page_title": ""
    }

    try:
        print(f"[{competitor['name']}] Navigating to {competitor['url']}...")
        await page.goto(competitor["url"], wait_until="networkidle", timeout=30000)

        # Wait for dynamic content to load
        await page.wait_for_timeout(2000)

        # Dismiss cookie banners if present
        for selector in ["[id*='accept']", "[class*='cookie'] button", "button[aria-label*='Accept']"]:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(500)
                    break
            except Exception:
                pass

        # Get full page HTML
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Extract page title
        title_tag = soup.find("title")
        result["page_title"] = title_tag.get_text(strip=True) if title_tag else ""

        # Remove script/style tags before text extraction
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Get clean text from main content
        main = soup.find("main") or soup.find("body")
        if main:
            result["raw_text"] = main.get_text(separator=" ", strip=True)[:5000]

        # Extract prices using regex
        price_pattern = r'\$[\d,]+(?:\.\d{2})?(?:\s*\/\s*(?:month|mo|year|yr|user))?'
        prices_found = re.findall(price_pattern, result["raw_text"], re.IGNORECASE)
        result["prices"] = list(set(prices_found))[:10]

        # Extract plan names (common patterns)
        plan_patterns = r'\b(Free|Starter|Basic|Pro|Plus|Business|Enterprise|Team|Growth|Scale)\b'
        plans_found = re.findall(plan_patterns, result["raw_text"])
        result["features"] = list(dict.fromkeys(plans_found))[:8]  # preserve order, dedupe

        print(f"[{competitor['name']}] ✓ Scraped. Prices found: {result['prices']}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"[{competitor['name']}] ✗ Error: {e}")

    finally:
        await browser.close()

    return result


async def run_scraper() -> list:
    """Run all scrapers concurrently"""
    print("\n🤖 Starting Competitor Intelligence Scraper Agent")
    print("=" * 50)

    async with async_playwright() as playwright:
        # Run scrapers concurrently (max 3 at a time)
        tasks = [scrape_page(playwright, c) for c in COMPETITORS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions
    clean_results = []
    for r in results:
        if isinstance(r, Exception):
            print(f"Task failed: {r}")
        else:
            clean_results.append(r)

    return clean_results


def save_results(results: list):
    """Save scraped results to JSON file (relative to this script's directory)"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, f"scrape_{timestamp}.json")

    with open(filename, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to {filename}")
    return filename


if __name__ == "__main__":
    results = asyncio.run(run_scraper())
    save_results(results)

    print("\n📊 Summary:")
    for r in results:
        status = "✓" if r["status"] == "success" else "✗"
        print(f"  {status} {r['name']}: {len(r['prices'])} prices, {len(r['features'])} plans")
