from uuid import uuid4

from pyrogram import Client
from pyrogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, ChosenInlineResult

from .. import genius
from ..db.models import *

ERROR_THUMB = 'https://i.imgur.com/RARF2nv.png'
NO_SONGS_FOUND = InlineQueryResultArticle(title='❌ No songs found!', thumb_url=ERROR_THUMB,
                                          description="Please try changing your search query.",
                                          input_message_content=InputTextMessageContent(
                                              message_text='❌ <b>No songs found.</b>'),
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='More info 🤖',
                                                                                                   url='https://t.me/LyricsSeekerBot?start=inline')],
                                                                             [InlineKeyboardButton(text='Search 🔎',
                                                                                                   switch_inline_query='')]]))

CACHE = {}

SCRAPING_MESSAGE = "⏳ <b>Getting song info... Please wait.</b>"
SCRAPING_KEYBOARD = InlineKeyboardMarkup([[InlineKeyboardButton("🤖", url=config.DEEP_LINKING + "scraping")]])


@Client.on_inline_query()
async def on_inline_query(_, query: InlineQuery):
    user: User = query.user
    text = query.query

    results = []

    try:
        with db_session:
            if len(text.strip()) < 2:
                results.append(NO_SONGS_FOUND)
            else:
                songs = genius.search(text, user, limit=20)[1]

                if len(songs) > 10:
                    songs = songs[:10]

                if len(songs) < 1:
                    results.append(NO_SONGS_FOUND)
                else:
                    for song in songs:
                        id = str(uuid4())
                        description = "by " + song.artist.name
                        results.append(InlineQueryResultArticle(title=song.title,
                                                                id=id,
                                                                input_message_content=InputTextMessageContent(
                                                                    message_text=SCRAPING_MESSAGE,
                                                                    disable_web_page_preview=False),
                                                                reply_markup=SCRAPING_KEYBOARD,
                                                                thumb_url=song.thumbnail,
                                                                description=description))

                        Queries(id=id, song=song)
                        commit()

            await query.answer(results, switch_pm_text='Settings 🤖', switch_pm_parameter='inline', cache_time=0,
                               is_personal=True)
    except Exception as e:
        print(e)


@Client.on_chosen_inline_result()
async def on_chosen_inline_result(client, chosen: ChosenInlineResult):
    id = chosen.result_id
    message_id = chosen.inline_message_id

    with db_session:
        query = Queries.get(id=id)

        if query:
            song = query.song

            await client.edit_inline_text(message_id, text=song.message(True),
                                          reply_markup=song.keyboard(menu=False),
                                          disable_web_page_preview=False)

            song.add_to_history(chosen.user)

            search = Search.select(lambda s: s.query.lower() == chosen.query.lower()).sort_by(
                lambda s: desc(s.creation_time))[:][0]
            search.add_to_history(chosen.user)
