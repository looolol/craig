import discord
import os
from common import setup_logging
from discord.ext import commands, tasks
from main import poll_rss_feed

logger = setup_logging()

# Discord Bot Token and Channel ID
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', 3600))


class Craig(discord.Client):
    async def on_ready(self):
        logger.info(f'Logged on as {self.user}\n')
        self.polling.start()

    @tasks.loop(seconds=POLLING_INTERVAL)
    async def polling(self):
        await poll_rss_feed(CHANNEL_ID)

    async def close(self):
        self.polling.stop()
        await super().close()


# Start the bot
if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    craig = Craig(intents=intents)
    craig.run(TOKEN)
