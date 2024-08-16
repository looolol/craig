import traceback
from io import BytesIO

import discord
from common import setup_logging
from fetcher import fetch_image

logger = setup_logging(__name__)

async def post_to_discord(channel, title, images, entry_id, session):
    logger.info(f'{entry_id} - Sending message to Discord channel {channel.id}')
    files = []
    for i, img in enumerate(images):
        img_data = await fetch_image(img, session)
        if img_data:
            image_file = BytesIO(img_data)
            image_file.name = f"image{i}.jpg"
            files.append(discord.File(fp=image_file, filename=image_file.name))
    try:
        await channel.send(content=title, files=files)
        logger.info(f'{entry_id} - Message sent successfully')
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")
        logger.error(traceback.format_exc())


async def post_all_to_discord(channel, entry, images, session):
    logger.info(f'{entry.id} - Posting to Discord: {entry.title}')
    post_title = f"# [{entry.title}](<{entry.link}>)"
    batch_size = 10

    if images:
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            await post_to_discord(channel, post_title, batch, entry.id, session)
    else:
        await channel.send(post_title)

    logger.info(f'{entry.id} - Finished posting to Discord\n')



