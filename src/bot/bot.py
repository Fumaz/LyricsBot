from pyrogram import Client

from . import config
from .db import models

client = Client(session_name=config.SESSION_NAME,
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                bot_token=config.BOT_TOKEN,
                plugins=dict(root=config.PLUGINS_FOLDER),
                workers=8)


def run():
    models.setup()
    client.run()
