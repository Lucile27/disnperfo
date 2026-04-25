import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo

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

    # Run scrapers sequentially to avoid OOM on Render free tier (512MB)
    amazon_data = await loop.run_in_executor(executor, scrape_amazon_top5)
    cadeaucity_data = await loop.run_in_executor(executor, scrape_cadeaucity_top5)

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

    if amazon is None and cadeaucity is None:
        # Data not ready yet (cold start) — return empty with a loading flag
        # The periodic_refresh task is already running in the background
        return {
            "amazon": [],
            "cadeaucity": [],
            "last_updated": "Chargement en cours... rechargez dans 1-2 minutes",
            "loading": True,
        }

    return {
        "amazon": [asdict(p) for p in (amazon or [])],
        "cadeaucity": [asdict(p) for p in (cadeaucity or [])],
        "last_updated": datetime.now(ZoneInfo("Europe/Brussels")).strftime("%d/%m/%Y %H:%M"),
    }


@app.post("/api/refresh")
async def force_refresh():
    await refresh_data()
    return {"status": "ok", "message": "Données rafraîchies"}
