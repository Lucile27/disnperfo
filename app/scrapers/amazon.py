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

SEARCH_URL = "https://www.amazon.com.be/s?k=Disney+Traditions+figurine"

# KPI weights
W_BADGE = 0.40
W_POSITION = 0.35
W_RATING = 0.15
W_REVIEWS = 0.10

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

                const link = item.querySelector('a[href*="/dp/"]');
                const href = link ? link.getAttribute('href') : '';

                const img = item.querySelector('.s-image, img[data-image-latency="s-product-image"]');
                const imgSrc = img ? img.src : '';

                const ratingMatch = text.match(/(\d[,.]\d)\s*\n/);
                const rating = ratingMatch ? parseFloat(ratingMatch[1].replace(',', '.')) : null;

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

                const priceMatch = text.match(/(\d+[,.]\d{2})\s*\u20ac/);
                const price = priceMatch ? priceMatch[1] + ' \u20ac' : '';

                const badgeEl = item.querySelector('.a-badge-text');
                const badge = badgeEl ? badgeEl.textContent.trim() : null;

                results.push({ name, href, imgSrc, rating, reviewCount, price, badge, position: results.length + 1 });
            }
            return results;
        }""")

        browser.close()

        # Compute KPI scores
        total = len(data)
        max_reviews = max((d["reviewCount"] for d in data), default=1) or 1

        for item in data:
            href = item["href"]
            if href and not href.startswith("http"):
                href = "https://www.amazon.com.be" + href

            # Badge: 1.0 if present, 0.0 if not
            s_badge = 1.0 if item["badge"] else 0.0
            # Position: best (1) = 1.0, worst (total) = 0.0
            s_position = (total - item["position"]) / max(total - 1, 1)
            # Rating: normalized 0-5 to 0-1
            s_rating = (item["rating"] / 5.0) if item["rating"] else 0.0
            # Reviews: normalized relative to max
            s_reviews = item["reviewCount"] / max_reviews

            kpi = (W_BADGE * s_badge + W_POSITION * s_position
                   + W_RATING * s_rating + W_REVIEWS * s_reviews)

            products.append({
                "name": item["name"],
                "price": item["price"],
                "rating": item["rating"],
                "review_count": item["reviewCount"],
                "url": href,
                "image_url": item["imgSrc"] or None,
                "badge": item["badge"],
                "kpi_score": round(kpi * 100, 1),
            })

except Exception as e:
    print(json.dumps({"error": str(e)}), file=sys.stderr)

products.sort(key=lambda p: p["kpi_score"], reverse=True)
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
                    kpi_score=d.get("kpi_score"),
                )
                for d in data
            ]
    except subprocess.TimeoutExpired:
        logger.error("Amazon scraper timed out")
    except Exception as e:
        logger.error("Amazon scraper failed: %s", e)

    return []
