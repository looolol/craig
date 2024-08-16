import discord
import os
from common import setup_logging
from discord.ext import tasks
from polling import poll_rss_feed

logger = setup_logging(__name__)

# Discord Bot Token and Channel ID
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', 3600))


class Craig(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.channel = None

    async def on_ready(self):
        logger.info(f'Logged on as {self.user}\n')
        self.channel = self.get_channel(CHANNEL_ID)
        if self.channel is None:
            logger.error(f'Channel with ID {CHANNEL_ID} not found.')
            await self.close()  # Close the bot if the channel is not found
            return
        self.polling.start()

    @tasks.loop(seconds=POLLING_INTERVAL)
    async def polling(self):
        if self.channel:
            await poll_rss_feed(self.channel)
        else:
            logger.error('Channel is not set. Polling task will not run.')

    async def close(self):
        logger.info('Stopping polling task...')
        self.polling.stop()
        await super().close()


# Start the bot
if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    craig = Craig(intents=intents)
    craig.run(TOKEN)
