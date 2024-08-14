import discord
import feedparser
import aiohttp
from io import BytesIO
import os
import logging
import time
import traceback
import json
import asyncio
import ssl

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Discord Bot Token and Channel ID
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

RSS_FEED = os.getenv('RSS_FEED')
POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', 3600))  # Default to 3600 seconds if not set

# Setup the Discord Client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

RATE_LIMIT_STATUS = 429

# Path for storing processed entry IDs
ID_FILE = 'processed_ids.json'

# Decode HTML entities
def decode_url(url):
    return url.replace("&amp;", "&")

def get_entry_id(entry):
    if '/' not in entry.id:
        return entry.id
    else:
        entry.id = entry.id.split('/')[-1].split("_")[-1]
        return entry.id

# Function to fetch and parse RSS feed
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
                    logging.error(f"Failed to fetch image: {url}, status code: {response.status}")
        except aiohttp.ClientError as e:
            logging.error(f"Client error occurred: {e}")
        except ssl.SSLError as e:
            logging.error(f"SSL error occurred: {e}")
        await asyncio.sleep(2)  # wait before retrying
    return None

# Function to extract image URLs from the Reddit post
async def extract_images(entry, session):
    logging.info(f'{entry.id} - Extracting images from post: {entry.title} / {entry.link}')
    images = []

    if entry.link:
        retry_attempts = 3
        for attempt in range(retry_attempts):
            try:
                async with session.get(f"{entry.link}.json") as response:
                    if response.status == RATE_LIMIT_STATUS:
                        logging.warning("Rate limit hit: Retrying...")
                        continue

                    if response.status == 200:
                        data = await response.json()
                        for obj in data:
                            for child in obj['data']['children']:
                                if child['kind'] == "t3":
                                    if 'preview' in child['data']:
                                        source = child['data']['preview']['images'][0]['source']
                                        img_link = decode_url(source['url'])
                                        images.append(img_link)

                                    if 'media_metadata' in child['data']:
                                        for media_metadata in child['data']['media_metadata'].values():
                                            if media_metadata.get('e') == 'Image':
                                                img_link = decode_url(media_metadata['s']['u'])
                                                images.append(img_link)
                        break
                    else:
                        logging.error(f"Bad response: {response.status}")
            except Exception as e:
                logging.error(f"Error during image extraction: {e}")
                logging.error(traceback.format_exc())
            await asyncio.sleep(2)  # wait before retrying

    logging.info(f'{entry.id} - Done! Extracted {len(images)} images:')
    for img in images:
        logging.info(f'{entry.id} -    {img}')
    return images

async def post_to_discord(channel, title, link, images, entry_id, session):
    logging.info(f'{entry_id} - Sending message to Discord channel {channel.id}')
    files = []
    for i, img in enumerate(images):
        img_data = await fetch_image(img, session)
        if img_data:
            image_file = BytesIO(img_data)
            image_file.name = f"image{i}.jpg"
            files.append(discord.File(fp=image_file, filename=image_file.name))

    try:
        await channel.send(content=title, files=files)
        logging.info(f'{entry_id} - Message sent successfully')
    except Exception as e:
        logging.error(f"Error sending message to Discord: {e}")
        logging.error(traceback.format_exc())

async def post_all_to_discord(channel, entry, images, session):
    logging.info(f'{entry.id} - Posting to Discord: {entry.title}')
    post_title = f"# [{entry.title}](<{entry.link}>)"
    batch_size = 10

    if images:
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            await post_to_discord(channel, post_title, entry.link, batch, entry.id, session)
    else:
        await channel.send(post_title)

    logging.info(f'{entry.id} - Finished posting to Discord\n')

def load_processed_ids():
    if os.path.exists(ID_FILE):
        with open(ID_FILE, 'r') as file:
            return set(json.load(file))
    return set()

def save_processed_ids(ids):
    with open(ID_FILE, 'w') as file:
        json.dump(list(ids), file)

async def poll_rss_feed(channel):
    processed_ids = load_processed_ids()

    logging.info(f'Polling Interval: {POLLING_INTERVAL}')
    async with aiohttp.ClientSession() as session:
        while True:
            print("\n")
            try:
                feed = fetch_rss_feed(RSS_FEED)
                
                new_entries = 0
                new_entry_ids = set()
                
                # First pass: Check for new entries
                for entry in feed.entries:
                    entry_id = get_entry_id(entry)
                    if entry_id not in processed_ids:
                        new_entry_ids.add(entry_id)
                        new_entries += 1

                if new_entries > 0:
                    logging.info(f'New entries found: {new_entries}\n')

                    entries_processed = 0
                    
                    # Process new entries in reverse order
                    for entry in reversed(feed.entries):
                        entry_id = get_entry_id(entry)
                        if entry_id in new_entry_ids:
                            logging.info(f'{entry_id} - Processing new entry: {entry.title} (ID: {entry_id})')
                            images = await extract_images(entry, session)
                            await post_all_to_discord(channel, entry, images, session)
                            
                            # Save ID immediately after processing
                            processed_ids.add(entry_id)
                            save_processed_ids(processed_ids)
                            entries_processed += 1

                    logging.info(f'New Entries Processed: {entries_processed}')        

                else:
                    logging.info('No new entries found')

            except Exception as e:
                logging.error(f"Error during RSS feed polling: {e}")
                logging.error(traceback.format_exc())

            await asyncio.sleep(POLLING_INTERVAL)

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')
    channel = client.get_channel(CHANNEL_ID)
    await poll_rss_feed(channel)

client.run(TOKEN)
