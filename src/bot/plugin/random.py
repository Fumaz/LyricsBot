from pyrogram import Client, filters

from bot.db.models import *


@Client.on_callback_query(filters.regex('^random_song$'))
async def on_random_callback(_, query):
    await query.answer()
    await query.edit_message_text(config.LOADING)

    with db_session:
        song = Song.select_random(1)[0]

        await query.edit_message_text(song.message(True), reply_markup=song.keyboard(menu=True),
                                      disable_web_page_preview=False)


@Client.on_message(filters.command('random'))
async def on_random_command(_, message):
    msg = await message.reply_text(config.LOADING)

    with db_session:
        song = Song.select_random(1)[0]

        await msg.edit_text(song.message(True), reply_markup=song.keyboard(menu=True),
                            disable_web_page_preview=False)
