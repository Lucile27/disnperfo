import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.cache import get_cached, set_cached
from app.scrapers.amazon import scrape_amazon_top5
from app.scrapers.cadeaucity import scrape_cadeaucity_top5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=2)


async def refresh_data():
    """Fetch fresh data from both sources using threads for sync Playwright."""
    logger.info("Refreshing data from sources...")
    loop = asyncio.get_event_loop()

    # Run both scrapers in parallel threads
    amazon_future = loop.run_in_executor(executor, scrape_amazon_top5)
    cadeaucity_future = loop.run_in_executor(executor, scrape_cadeaucity_top5)

    amazon_data, cadeaucity_data = await asyncio.gather(
        amazon_future, cadeaucity_future, return_exceptions=True
    )

    if isinstance(amazon_data, Exception):
        logger.error("Amazon scraper error: %s", amazon_data)
        amazon_data = []
    if isinstance(cadeaucity_data, Exception):
        logger.error("CadeauCity scraper error: %s", cadeaucity_data)
        cadeaucity_data = []

    set_cached("amazon", amazon_data)
    set_cached("cadeaucity", cadeaucity_data)

    logger.info(
        "Data refreshed: %d Amazon, %d CadeauCity",
        len(amazon_data),
        len(cadeaucity_data),
    )


async def periodic_refresh():
    """Background task to refresh data every 6 hours."""
    while True:
        try:
            await refresh_data()
        except Exception as e:
            logger.error("Periodic refresh failed: %s", e)
        await asyncio.sleep(6 * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(periodic_refresh())
    yield
    task.cancel()


app = FastAPI(title="DisnPerfo", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/top5")
async def get_top5():
    amazon = get_cached("amazon")
    cadeaucity = get_cached("cadeaucity")

    if amazon is None or cadeaucity is None:
        await refresh_data()
        amazon = get_cached("amazon") or []
        cadeaucity = get_cached("cadeaucity") or []

    return {
        "amazon": [asdict(p) for p in amazon],
        "cadeaucity": [asdict(p) for p in cadeaucity],
        "last_updated": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


@app.post("/api/refresh")
async def force_refresh():
    await refresh_data()
    return {"status": "ok", "message": "Données rafraîchies"}
