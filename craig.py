import discord
import feedparser
import requests
from io import BytesIO
from bs4 import BeautifulSoup
import os

# Discord Bot Token
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID')) #Spoilers

# Setup the Discord Client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Decode HTML entities
def decode_url(url):
	return url.replace("&amp;", "&")

# Function to fetch and parse RSS feed
def fetch_rss_feed(url):
	print('Fetching RSS Feed...')
	feed = feedparser.parse(url)
	print('Done!')
	return feed

# Function to extract image URLs from the Reddit post
def extract_images(entry):
	print('')
	print(f'Extracting images...{entry.title} / {entry.link}')
	images = []

	# fetch post json data
	if entry.link:

		response = requests.get(f"{entry.link}.json")

		# If reddit api returns rate limit error, then retry till success
		if response.status_code == 429:
			print("Rate limit Hit: Retrying...")

			while (response.status_code == 429):
				response = requests.get(f"{entry.link}.json")

		if response.status_code == 200:
			data = response.json()


			# Extract all images from the Reddit posts comment's metadata
			try:
				# For all children in the post data
				for obj in data:
					for child in obj['data']['children']:

						# Filter out comments
						if child['kind'] == "t3":

							if 'preview' in child['data']:
								source = child['data']['preview']['images'][0]['source']

								img_link = decode_url(source['url'])
								print(f'\timg_link')
								images.append(img_link)


							if 'media_metadata' in child['data']:
								# Look for Image metadata
								for media_metadata in child['data']['media_metadata'].values():

									# Meta data contains non-descriptive keys
									# 'E' is media type?, checking for Images
									if 'e' in media_metadata and media_metadata['e'] == 'Image':
										# 'e' contains two children, 'p' and 's'.
										# 'p' have different sizes of the image
										# 's' I belive is the source picture
										# 'u' contains the link that is needed
										if 's' in media_metadata and 'u' in media_metadata['s']:
											img_link = decode_url(media_metadata['s']['u'])
											print(f'\timg_link')
											images.append(img_link)
									else:
										print(f"No link found: {media_metadata}")
			except Exception as e:
				print(f"Error parsing object: {e}")
		else:
			print(f"Bad response: {response.status_code}")

	print(f'Done! count:{len(images)}')
	return images

async def post_all_to_discord(channel, title, link, images):
	print('Posting to Alldiscord...')

	post_title = f"# {title}\n<{link}>"
	batch_size = 10

	if images:
		for i in range(0, len(images), batch_size):
			batch = images[i:i+batch_size]
			await post_to_discord(channel, post_title, link, batch)
	else:
		await channel.send(post_title)

	print('Done!')

# Function to send a message to Discord
async def post_to_discord(channel, title, link, images):
	print('\tPosting to discord...')

	files = []
	i = 0
	for img in images:
		response = requests.get(img)
		if response.status_code == 200:
			# Create a file-like object
			image_file = BytesIO(response.content)
			image_file.name = "image.jpg"

			# Create a discord.File object
			file = discord.File(fp=image_file, filename=f"image{i}.jpg")
			i = i + 1

			files.append(file)

	
	await channel.send(title, files=files)
	print('\tDone!')

@client.event
async def on_ready():
	print(f'Logged in as {client.user}')
	channel = client.get_channel(CHANNEL_ID)

	# Example Reddit RSS feed URL (Replace with your desired subreddit)
	rss_url = 'https://www.reddit.com/search.rss?q=flair%3Aspoiler+%28subreddit%3AmagicTCG%29&include_over_18=on&sort=new&t=all'
	feed = fetch_rss_feed(rss_url)

	print(f'Num entries: {len(feed.entries)}')
	    
	for entry in feed.entries:
		images = extract_images(entry)

		await post_all_to_discord(channel, entry.title, entry.link, images)

client.run(TOKEN)