import asyncio
import traceback
import os

from common import setup_logging, RATE_LIMIT_STATUS, decode_url

logger = setup_logging(__name__)


UPVOTE_THRESH0LD = int(os.getenv('UPVOTE_THRESHOLD', 5))


async def parse_entry(entry, session):
    logger.info(f'{entry.id} - Extracting images from post: {entry.title} / {entry.link}')
    images = []

    if entry.link:
        retry_attempts = 3
        for attempt in range(retry_attempts):
            try:
                async with session.get(f"{entry.link}.json") as response:
                    if response.status == RATE_LIMIT_STATUS:
                        logger.warning("Rate limit hit: Retrying...")
                        continue

                    if response.status == 200:
                        data = await response.json()
                        for obj in data:
                            for child in obj['data']['children']:
                                if child['kind'] == "t3":
                                    if 'ups' in child['data'] and child['data']['ups'] > UPVOTE_THRESH0LD: # Upvote Filter
                                        if 'preview' in child['data']:
                                            source = child['data']['preview']['images'][0]['source']
                                            img_link = decode_url(source['url'])
                                            images.append(img_link)

                                        if 'media_metadata' in child['data']:
                                            for media_metadata in child['data']['media_metadata'].values():
                                                if media_metadata.get('e') == 'Image':
                                                    img_link = decode_url(media_metadata['s']['u'])
                                                    images.append(img_link)
                                    else:
                                        logger.info(f'{entry.id} - [SKIPPED] - minimum score not reached')
                                        return False, None
                        break
                    else:
                        logger.error(f"Bad response: {response.status}")
            except Exception as e:
                logger.error(f"Error during image extraction: {e}")
                logger.error(traceback.format_exc())
            await asyncio.sleep(2)  # wait before retrying

    logger.info(f'{entry.id} - Done! Extracted {len(images)} images:')
    for img in images:
        logger.info(f'{entry.id} -    {img}')
    return True, images
