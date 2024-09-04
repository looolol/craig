import discord
import os
from common import setup_logging
from discord.ext import tasks
from polling import poll_rss_feed
from datetime import datetime, time

logger = setup_logging(__name__)

# Discord Bot Token and Channel ID
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', 3600))

# Quiet hours (configured in 24-hour format as 'HH:MM')
QUIET_HOUR_START = os.getenv('QUIET_HOUR_START', '22:00')
QUIET_HOUR_END = os.getenv('QUIET_HOUR_END', '07:00')

def within_quiet_hours():
    now = datetime.now().time()
    start_hour, start_minute = map(int, QUIET_HOUR_START.split(':'))
    end_hour, end_minute = map(int, QUIET_HOUR_END.split(':'))

    start_time = time(start_hour, start_minute)
    end_time = time(end_hour, end_minute)

    if start_time < end_time:
        return start_time <= now <= end_time
    else:
        return now >= start_time or now <= end_time



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
        if within_quiet_hours():
            logger.info('Within quiet hours, skipping this polling cycle.')
            return

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
