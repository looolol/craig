
import traceback
import aiohttp
import os

from parser import parse_entry
from common import get_entry_id, load_processed_ids, save_processed_ids, setup_logging
from fetcher import fetch_rss_feed
from discord_service import post_all_to_discord

logger = setup_logging(__name__)

RSS_FEED = os.getenv('RSS_FEED')


def get_new_entries(feed, processed_ids):
    new_entries = []
    for entry in feed.entries:
        entry_id = get_entry_id(entry)
        if entry_id not in processed_ids:
            new_entries.append(entry)

    return new_entries


async def process_new_entries(entries, processed_ids, channel):
    logger.info(f'New entries found: {len(entries)}\n')

    num_processed = 0
    async with aiohttp.ClientSession() as session:
        for entry in entries:
            entry_id = get_entry_id(entry)
            logger.info(f'{entry_id} - Processing new entry: {entry.title} (ID: {entry_id})')

            images = await parse_entry(entry, session)
            await post_all_to_discord(channel, entry, images, session)

            processed_ids.add(entry_id)
            save_processed_ids(processed_ids)
            num_processed = num_processed + 1

    logger.info(f'New Entries Processed: {num_processed}')


async def poll_rss_feed(channel):
    logger.info('Starting polling...')
    processed_ids = load_processed_ids()

    try:
        feed = fetch_rss_feed(RSS_FEED)
        new_entries = get_new_entries(feed, processed_ids)

        if new_entries:
            await process_new_entries(new_entries[::-1], processed_ids, channel)
        else:
            logger.info('No new entries found')
    except Exception as e:
        logger.error(f"Error during RSS feed polling: {e}")
        logger.error(traceback.format_exc())

    logger.info('Polling Ended\n')
