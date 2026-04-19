import json
import logging
import os
import subprocess
import sys
from app.models import Product

logger = logging.getLogger(__name__)

_SCRIPT = r'''
import json
import re
import sys
from playwright.sync_api import sync_playwright

SEARCH_URL = "https://www.amazon.com.be/s?k=Disney+Traditions+figurine"

products = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="fr-BE",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = context.new_page()
        page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("[data-component-type='s-search-result']", timeout=15000)

        data = page.evaluate(r"""() => {
            const items = document.querySelectorAll('[data-component-type="s-search-result"]');
            const results = [];
            for (let i = 0; i < Math.min(items.length, 15); i++) {
                const item = items[i];
                const text = item.innerText || '';

                // Name: find the line that looks like a product name
                // Skip badge lines like "N°1 des ventes", "Choix d'Amazon", etc.
                const lines = text.split('\n').filter(l => l.trim());
                let name = '';
                for (const line of lines) {
                    const l = line.trim();
                    if (l.length < 10) continue;
                    if (/^N°\d|^Choix|^Sponsoris|^Meilleur/i.test(l)) continue;
                    if (/étoile|prix|livraison|panier|vendeur/i.test(l)) continue;
                    name = l;
                    break;
                }
                if (!name) continue;

                // URL: first product link
                const link = item.querySelector('a[href*="/dp/"]');
                const href = link ? link.getAttribute('href') : '';

                // Image
                const img = item.querySelector('.s-image, img[data-image-latency="s-product-image"]');
                const imgSrc = img ? img.src : '';

                // Rating: pattern "X,X" before "étoile"
                const ratingMatch = text.match(/(\d[,.]\d)\s*\n/);
                const rating = ratingMatch ? parseFloat(ratingMatch[1].replace(',', '.')) : null;

                // Review count: pattern "(3,3 k)" or "(372)"
                const reviewMatch = text.match(/\(([0-9][0-9,.]*\s*k?)\)/i);
                let reviewCount = 0;
                if (reviewMatch) {
                    let rv = reviewMatch[1].trim();
                    if (rv.toLowerCase().includes('k')) {
                        rv = rv.toLowerCase().replace('k', '').replace(',', '.').trim();
                        reviewCount = Math.round(parseFloat(rv) * 1000);
                    } else {
                        reviewCount = parseInt(rv.replace(/[^\d]/g, ''), 10) || 0;
                    }
                }

                // Price: pattern "XX,XX €"
                const priceMatch = text.match(/(\d+[,.]\d{2})\s*\u20ac/);
                const price = priceMatch ? priceMatch[1] + ' \u20ac' : '';

                // Best seller badge
                const badgeEl = item.querySelector('.a-badge-text');
                const badge = badgeEl ? badgeEl.textContent.trim() : null;

                results.push({ name, href, imgSrc, rating, reviewCount, price, badge });
            }
            return results;
        }""")

        for item in data:
            href = item["href"]
            if href and not href.startswith("http"):
                href = "https://www.amazon.com.be" + href
            products.append({
                "name": item["name"],
                "price": item["price"],
                "rating": item["rating"],
                "review_count": item["reviewCount"],
                "url": href,
                "image_url": item["imgSrc"] or None,
                "badge": item["badge"],
            })

        browser.close()
except Exception as e:
    print(json.dumps({"error": str(e)}), file=sys.stderr)

products.sort(key=lambda p: p["review_count"], reverse=True)
print(json.dumps(products[:5], ensure_ascii=False))
'''


def scrape_amazon_top5() -> list[Product]:
    """Run Amazon scraper as a subprocess to avoid Windows asyncio issues."""
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
            logger.warning("Amazon scraper stderr: %s", stderr[:500])

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
        logger.error("Amazon scraper timed out")
    except Exception as e:
        logger.error("Amazon scraper failed: %s", e)

    return []
