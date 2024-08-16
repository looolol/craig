import feedparser
import aiohttp
import time
import ssl
import asyncio

from common import RATE_LIMIT_STATUS, setup_logging

logger = setup_logging(__name__)


async def retry_request(callable, retries=3, delay=2):
    for attempt in range(retries):
        try:
            return await callable()
        except (aiohttp.ClientError, ssl.SSLError) as e:
            logger.error(f'Error occurred: {e}')
            if attempt < retries - 1:
                logger.warning(f'Retrying... ({attempt + 1}/{retries})')
                await asyncio.sleep(delay)
            else:
                raise


def fetch_rss_feed(url):
    logger.info('Fetching RSS Feed...')
    start_time = time.time()
    feed = feedparser.parse(url)
    logger.info(f'RSS Feed fetched in {time.time() - start_time:.2f} seconds')
    return feed


async def fetch_image(url, session):
    async def fetch():
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            elif response.status == RATE_LIMIT_STATUS:
                logger.warning("Rate limit hit: Retrying...")
                raise aiohttp.ClientError("Rate limit hit")
            else:
                logger.error(f'Failed to fetch image: {url}, status code: {response.status}')
                return None

    return await retry_request(fetch)

