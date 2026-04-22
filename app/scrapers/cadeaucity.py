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

BASE_URL = "https://www.cadeaucity.com"
CATEGORY_URL = f"{BASE_URL}/fr/22-figurines-disney-traditions"

# KPI weights
W_RATING = 0.35
W_REVIEWS = 0.30
W_NEW = 0.20
W_STOCK = 0.15

products = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(CATEGORY_URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)

        # Step 1: Get product URLs from category page
        catalog = page.evaluate(r"""() => {
            const links = document.querySelectorAll('a[href*="/figurines-disney-traditions/"]');
            const seen = new Set();
            const data = [];

            for (const a of links) {
                const href = a.href;
                if (seen.has(href) || !a.textContent.trim()) continue;
                seen.add(href);

                const card = a.closest('[class*="cursor-pointer"]') || a.parentElement;
                if (!card) continue;

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

                data.push({ name, href, img });
                if (data.length >= 15) break;
            }
            return data;
        }""")
        page.close()

        # Step 2: Visit each product page for detailed info
        raw = []
        for item in catalog:
            try:
                pg = browser.new_page()
                pg.goto(item["href"], wait_until="networkidle", timeout=30000)
                pg.wait_for_timeout(2000)

                detail = pg.evaluate(r"""() => {
                    const body = document.body.innerText;

                    // Review count: "( X Commentaires )"
                    const countMatch = body.match(/\(\s*(\d+)\s*Commentaire/i);
                    const reviewCount = countMatch ? parseInt(countMatch[1]) : 0;

                    // Rating: "Note moyenne X / 5"
                    const ratingMatch = body.match(/Note moyenne\s*(\d+(?:[.,]\d+)?)\s*\/\s*5/);
                    const rating = ratingMatch ? parseFloat(ratingMatch[1].replace(',', '.')) : null;

                    // Price
                    const priceEl = document.querySelector('[class*="price"]') || null;
                    const priceText = priceEl ? priceEl.textContent : body;
                    const priceMatch = priceText.match(/(\d+[,.]\d{2})\s*\u20ac/);
                    const price = priceMatch ? priceMatch[1] + ' \u20ac' : '';

                    // In stock
                    const inStock = body.includes('En stock');

                    // New badge
                    const isNew = body.includes('NOUVEAU');

                    return { reviewCount, rating, price, inStock, isNew };
                }""")
                pg.close()

                raw.append({
                    "name": item["name"],
                    "url": item["href"],
                    "image_url": item["img"] or None,
                    "price": detail["price"],
                    "rating": detail["rating"],
                    "review_count": detail["reviewCount"],
                    "in_stock": detail["inStock"],
                    "is_new": detail["isNew"],
                })
            except Exception as e:
                print(json.dumps({"warn": f"CadeauCity detail error: {e}"}), file=sys.stderr)

        browser.close()

        # Step 3: Compute KPI scores
        max_reviews = max((r["review_count"] for r in raw), default=1) or 1

        for item in raw:
            s_rating = (item["rating"] / 5.0) if item["rating"] else 0.0
            s_reviews = item["review_count"] / max_reviews
            s_new = 1.0 if item["is_new"] else 0.0
            s_stock = 1.0 if item["in_stock"] else 0.0

            kpi = (W_RATING * s_rating + W_REVIEWS * s_reviews
                   + W_NEW * s_new + W_STOCK * s_stock)

            badge_parts = []
            if item["in_stock"]:
                badge_parts.append("En stock")
            if item["is_new"]:
                badge_parts.append("Nouveau")

            products.append({
                "name": item["name"],
                "price": item["price"],
                "rating": item["rating"],
                "review_count": item["review_count"],
                "url": item["url"],
                "image_url": item["image_url"],
                "badge": " | ".join(badge_parts) if badge_parts else None,
                "kpi_score": round(kpi * 100, 1),
            })

except Exception as e:
    print(json.dumps({"error": str(e)}), file=sys.stderr)

products.sort(key=lambda p: p["kpi_score"], reverse=True)
print(json.dumps(products[:5], ensure_ascii=False))
'''


def scrape_cadeaucity_top5() -> list[Product]:
    """Run CadeauCity scraper as a subprocess."""
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-c", _SCRIPT],
            capture_output=True, timeout=180, env=env,
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
                    kpi_score=d.get("kpi_score"),
                )
                for d in data
            ]
    except subprocess.TimeoutExpired:
        logger.error("CadeauCity scraper timed out")
    except Exception as e:
        logger.error("CadeauCity scraper failed: %s", e)

    return []
