import json
import logging
import os
import subprocess
import sys
from app.models import Product

logger = logging.getLogger(__name__)

_SCRIPT = r'''
import json
import sys
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.cadeaucity.com"
CATEGORY_URL = f"{BASE_URL}/fr/22-figurines-disney-traditions"

products = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(CATEGORY_URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)

        raw = page.evaluate(r"""() => {
            const links = document.querySelectorAll('a[href*="/figurines-disney-traditions/"]');
            const seen = new Set();
            const data = [];

            for (const a of links) {
                const href = a.href;
                if (seen.has(href) || !a.textContent.trim()) continue;
                seen.add(href);

                const card = a.closest('[class*="cursor-pointer"]') || a.parentElement;
                if (!card) continue;

                const cardText = card.innerText || '';
                const name = a.textContent.trim();
                if (name.length < 5) continue;

                const imgs = card.querySelectorAll('img');
                let img = '';
                for (const i of imgs) {
                    const src = i.src || i.dataset.src || '';
                    if (src && !src.includes('svg') && src.startsWith('http')) {
                        img = src;
                        break;
                    }
                }

                const priceMatch = cardText.match(/(\d+[,.]\d+)\s*\u20ac/);
                const price = priceMatch ? priceMatch[1] + ' \u20ac' : '';

                const ratingMatch = cardText.match(/\((\d+[.,]\d+)\)/);
                const rating = ratingMatch ? parseFloat(ratingMatch[1].replace(',', '.')) : null;

                const inStock = cardText.includes('En stock');

                data.push({ name, href, img, price, rating, inStock });
                if (data.length >= 10) break;
            }
            return data;
        }""")

        for item in raw:
            products.append({
                "name": item["name"],
                "price": item["price"],
                "rating": item["rating"],
                "review_count": 1 if item["rating"] else 0,
                "url": item["href"],
                "image_url": item["img"] or None,
                "badge": "En stock" if item["inStock"] else None,
            })

        browser.close()
except Exception as e:
    print(json.dumps({"error": str(e)}), file=sys.stderr)

products.sort(key=lambda p: (p["rating"] or 0, 1 if p["badge"] == "En stock" else 0), reverse=True)
print(json.dumps(products[:5], ensure_ascii=False))
'''


def scrape_cadeaucity_top5() -> list[Product]:
    """Run CadeauCity scraper as a subprocess."""
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-c", _SCRIPT],
            capture_output=True, timeout=60, env=env,
        )

        stderr = result.stderr.decode("utf-8", errors="replace")
        stdout = result.stdout.decode("utf-8", errors="replace")

        if stderr:
            logger.warning("CadeauCity scraper stderr: %s", stderr[:500])

        if stdout.strip():
            data = json.loads(stdout.strip())
            return [
                Product(
                    name=d["name"], price=d["price"], rating=d["rating"],
                    review_count=d["review_count"], url=d["url"],
                    image_url=d["image_url"], badge=d["badge"],
                )
                for d in data
            ]
    except subprocess.TimeoutExpired:
        logger.error("CadeauCity scraper timed out")
    except Exception as e:
        logger.error("CadeauCity scraper failed: %s", e)

    return []
