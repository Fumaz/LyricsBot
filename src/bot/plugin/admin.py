from pyrogram import Client, filters

from bot import tfilters
from bot.db.models import *


@Client.on_callback_query(filters.regex('^ban_') & tfilters.admin())
async def on_ban(client, callback):
    with db_session:
        user_id = int(callback.data[len('ban_'):])
        user = User.get(id=user_id)

        user.is_banned = True

        await callback.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("Unban User ✅", callback_data=f"unban_{user.id}")]]))

        try:
            await client.send_message(user.id, '❌ <b>You have been banned from this bot.</b>')
        except:
            pass


@Client.on_callback_query(filters.regex('^unban_') & tfilters.admin())
async def on_unban(client, callback):
    with db_session:
        user_id = int(callback.data[len('unban_'):])
        user = User.get(id=user_id)

        user.is_banned = False

        await callback.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("Ban User ❌", callback_data=f"ban_{user.id}")]]))

        try:
            await client.send_message(user.id, '✅ <b>You have been unbanned from this bot.</b>')
        except:
            pass


@Client.on_message(filters.command('stats') & tfilters.admin())
async def on_stats(_, message):
    with db_session:
        users = User.select().count()
        songs = Song.select().count()
        albums = Album.select().count()
        artists = Artist.select().count()
        lyrics = Lyrics.select(lambda l: l.text and l.text != 'Lyrics not found.').count()
        searches = Search.select().count()

        await message.reply_text(f"<b>Bot Stats</b> 🦠\n"
                                 f"\n"
                                 f"👥 Users » <code>{users}</code>\n"
                                 f"🎵 Songs » <code>{songs}</code>\n"
                                 f"💽 Albums » <code>{albums}</code>\n"
                                 f"👩‍🎤 Artists » <code>{artists}</code>\n"
                                 f"📝 Lyrics » <code>{lyrics}</code>\n"
                                 f"🔎 Searches » <code>{searches}</code>")
