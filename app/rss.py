import feedparser
import aiohttp
import logging
import time
import ssl
import asyncio

RATE_LIMIT_STATUS = 429


def fetch_rss_feed(url):
    logging.info('Fetching RSS Feed...')
    start_time = time.time()
    feed = feedparser.parse(url)
    logging.info(f'RSS Feed fetched in {time.time() - start_time:.2f} seconds')
    return feed


async def fetch_image(url, session):
    retry_attempts = 3
    for attempt in range(retry_attempts):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                elif response.status == RATE_LIMIT_STATUS:
                    logging.warning("Rate limit hit: Retrying...")
                    continue
                else:
                    logging.error(f'Failed to fetch image: {url}, status code: {response.status}')
        except aiohttp.ClientError as e:
            logging.error(f'Client error occurred: {e}')
        except ssl.SSLError as e:
            logging.error(f'SSL error occurred: {e}')
        await asyncio.sleep(2)  # wait before retrying
    return None
