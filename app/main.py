import logging
import traceback
import aiohttp
import os
from common import get_entry_id, load_processed_ids, save_processed_ids
from rss import fetch_rss_feed, fetch_image
from discord_service import post_all_to_discord

RSS_FEED = os.getenv('RSS_FEED')


def get_new_entries(feed, processed_ids):
    new_entries = []
    for entry in feed.entries:
        entry_id = get_entry_id(entry)
        if entry_id not in processed_ids:
            new_entries.append(entry)

    return new_entries


async def process_new_entries(entries, processed_ids, channel):
    logging.info(f'New entries found: {len(entries)}\n')

    async with aiohttp.ClientSession() as session:
        for entry in entries:
            entry_id = get_entry_id(entry)
            logging.info(f'{entry_id} - Processing new entry: {entry.title} (ID: {entry_id})')

            images = await fetch_image(entry, session)
            await post_all_to_discord(channel, entry, images, session)

            processed_ids.add(entry_id)
            save_processed_ids(processed_ids)

    logging.info(f'New Entries Processed: {len(processed_ids)}')


async def poll_rss_feed(channel):
    logging.info('Starting polling...')
    processed_ids = load_processed_ids()

    try:
        feed = fetch_rss_feed(RSS_FEED)
        new_entries = get_new_entries(feed, processed_ids)

        if new_entries:
            await process_new_entries(new_entries[::-1], processed_ids, channel)
        else:
            logging.info('No new entries found')
    except Exception as e:
        logging.error(f"Error during RSS feed polling: {e}")
        logging.error(traceback.format_exc())

    logging.info('Polling Ended')
