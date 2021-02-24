from datetime import timedelta

from telegraph import Telegraph

API_ID = 123456  # Insert your API ID
API_HASH = ""  # Insert your API Hash

BOT_TOKEN = ''  # Insert your bot token
BOT_USERNAME = ''  # Insert your bot's username
SESSION_NAME = 'session'

DEEP_LINKING = f'https://t.me/{BOT_USERNAME}?start='
INVISIBLE_CHAR = '⠀'

TELEGRAPH_TOKEN = ''  # Insert your Telegraph API Token
API_KEY = ''  # Insert your Genius API Key

DB_HOST = 'postgres'
DB_NAME = 'lyrics'
DB_USER = 'postgres'
DB_PASSW = ''

DB_CON = {'provider': 'postgres', 'user': DB_USER, 'password': DB_PASSW, 'host': DB_HOST, 'database': DB_NAME}

PACKAGE_DIR = 'bot/'
PLUGINS_FOLDER = PACKAGE_DIR + 'plugin'

MAX_CACHE_TIME = timedelta(days=1)

TELEGRAPH = Telegraph(access_token=TELEGRAPH_TOKEN)

BACK = 'Back ↩️'
MENU = 'Menu 🏘'

LYRICS_NOT_FOUND = 'Lyrics not found.'
LOADING = '⏳ <b>Loading...</b>'
