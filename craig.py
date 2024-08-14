import discord
import feedparser
import aiohttp
from io import BytesIO
import os
import logging
import time
import traceback
import uuid


# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Discord Bot Token and Channel ID
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))  # Spoilers

# Setup the Discord Client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

RATE_LIMIT_STATUS = 429

# Decode HTML entities
def decode_url(url):
    return url.replace("&amp;", "&")

# Function to fetch and parse RSS feed
def fetch_rss_feed(url):
    logging.info('Fetching RSS Feed...')
    start_time = time.time()
    feed = feedparser.parse(url)
    logging.info(f'RSS Feed fetched in {time.time() - start_time:.2f} seconds')
    return feed

async def fetch_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            elif response.status == RATE_LIMIT_STATUS:
                logging.warning("Rate limit hit: Retrying...")
                while response.status == RATE_LIMIT_STATUS:
                    async with session.get(url) as retry_response:
                        if retry_response.status == 200:
                            return await retry_response.read()
            else:
                logging.error(f"Failed to fetch image: {url}, status code: {response.status}")
                return None

# Function to extract image URLs from the Reddit post
async def extract_images(entry):
    logging.info(f'{entry.id} - Extracting images from post: {entry.title} / {entry.link}')
    images = []

    # Fetch post JSON data
    if entry.link:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{entry.link}.json") as response:
                if response.status == RATE_LIMIT_STATUS:
                    logging.warning("Rate limit hit: Retrying...")
                    while response.status == RATE_LIMIT_STATUS:
                        async with session.get(f"{entry.link}.json") as response:
                            pass

                if response.status == 200:
                    data = await response.json()

                    try:
                        for obj in data:
                            for child in obj['data']['children']:
                                if child['kind'] == "t3":

                                    # Handle Preview Images
                                    if 'preview' in child['data']:
                                        source = child['data']['preview']['images'][0]['source']
                                        img_link = decode_url(source['url'])
                                        images.append(img_link)

                                    # Handle Metadata
                                    if 'media_metadata' in child['data']:
                                        for media_metadata in child['data']['media_metadata'].values():
                                            if media_metadata.get('e') == 'Image':
                                                img_link = decode_url(media_metadata['s']['u'])
                                                images.append(img_link)
                    except Exception as e:
                        logging.error(f"Error parsing object: {e}")
                        logging.error(traceback.format_exc())
                else:
                    logging.error(f"Bad response: {response.status}")

    logging.info(f'{entry.id} - Done! Extracted {len(images)} images:')
    for img in images:
        logging.info(f'{entry.id} -    {img}')
    return images

async def post_all_to_discord(channel, entry, images):
    logging.info(f'{entry.id} - Posting to Discord: {entry.title}')
    post_title = f"# [{entry.title}](<{entry.link}>)"
    batch_size = 10

    if images:
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            await post_to_discord(channel, post_title, entry.link, batch, entry.id)
    else:
        await channel.send(post_title)

    logging.info(f'{entry.id} - Finished posting to Discord\n\n')

# Function to send a message to Discord
async def post_to_discord(channel, title, link, images, entry_id):
    logging.info(f'{entry_id} -   Sending message to Discord channel {channel.id}')
    files = []
    for i, img in enumerate(images):
        img_data = await fetch_image(img)
        if img_data:
            image_file = BytesIO(img_data)
            image_file.name = f"image{i}.jpg"
            files.append(discord.File(fp=image_file, filename=image_file.name))

    await channel.send(content=title, files=files)
    logging.info(f'{entry_id} -   Message sent successfully')

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')
    channel = client.get_channel(CHANNEL_ID)

    rss_url = 'https://www.reddit.com/search.rss?q=flair%3Aspoiler+%28subreddit%3AmagicTCG%29&include_over_18=on&sort=new&t=all'
    feed = fetch_rss_feed(rss_url)

    logging.info(f'Number of entries in feed: {len(feed.entries)}\n\n')

    for entry in feed.entries:
        entry.id = uuid.uuid4()  # Add a unique ID for each entry
        images = await extract_images(entry)
        await post_all_to_discord(channel, entry, images)

client.run(TOKEN)
