from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup

from bot import keyboards

MESSAGE = ("<b>Info 📦</b>\n"
           "\n"
           "Bot developed in <code>Python</code> by <a href='https://t.me/Fumaz'>Fumaz</a>.\n"
           "The source code is available on <a href='https://github.com/Fumaz/LyricsBot'>GitHub</a>")


@Client.on_callback_query(filters.regex('^info$'))
async def on_info(_, query):
    await query.answer()
    await query.edit_message_text(MESSAGE, reply_markup=InlineKeyboardMarkup([[keyboards.menu]]),
                                  disable_web_page_preview=True)
