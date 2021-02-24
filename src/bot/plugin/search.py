from pyrogram import Client, filters

from bot import genius
from bot import tfilters
from bot.db.models import *

SEARCH_MESSAGE = "💭 <b>Type the song's name, artist or album.</b>"
SEARCHING_MESSAGE = "⏳ <b>Searching... please wait.</b>"

NO_SONGS_FOUND = "❌ <b>No songs found!</b>"

RESULTS_PER_PAGE = 5

CACHE = {}


@Client.on_callback_query(filters.regex('^search_song$'))
async def on_search_callback(_, callback):
    await callback.answer()
    await callback.edit_message_text(SEARCH_MESSAGE, reply_markup=InlineKeyboardMarkup([[keyboards.menu]]))

    callback.user.set_action('search_song')


@Client.on_message(filters.command('search'))
async def on_search_message(_, message):
    if len(message.command) < 2:
        await message.reply_text(SEARCH_MESSAGE, reply_markup=InlineKeyboardMarkup([[keyboards.menu]]))

        message.user.set_action('search_song')
    else:
        message.user.reset_action()
        query = ' '.join(message.command[1:]).strip()

        results = []

        to_delete = await message.reply_text(SEARCHING_MESSAGE)

        with db_session:
            if len(query) >= 3:
                search, results = genius.search(query, message.user, 'private')

            if len(results) < 1:
                await message.reply_text(NO_SONGS_FOUND, reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Retry 🔄', callback_data='search_song')],
                     [keyboards.menu]]))
                return

            CACHE[message.user.id] = {'search_results': results, 'search_page': 0}

            msg = ("🎵 <b>I found</b> <code>{songs}</code> <b>songs.</b>\n"
                   "\n"
                   "<i>Page</i> <code>{page}</code> <i>of</i> <code>{pages}</code><i>.</i>")

            msg = msg.format(songs=len(results), page=1, pages=len(
                [results[i:i + RESULTS_PER_PAGE] for i in range(0, len(results), RESULTS_PER_PAGE)]))

            message.user.set_back_status('search_page_' + str(CACHE[message.user.id]['search_page']))
            await to_delete.delete()
            await message.reply_text(msg, reply_markup=create_keyboard(results, 0, 'search_song'))

            search.add_to_history(message.user)


@Client.on_message(tfilters.action('search_song') & filters.private & ~filters.edited & filters.text)
async def on_search_song(_, message):
    if message.text.startswith('/'):
        return

    user = message.user
    message.user.reset_action()

    to_delete = await message.reply_text(SEARCHING_MESSAGE)

    text = message.text.strip()
    results = []

    with db_session:
        if len(text) >= 3:
            search, results = genius.search(text, message.user, 'private')

        if len(results) < 1:
            await message.reply_text(NO_SONGS_FOUND, reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton('Retry 🔄', callback_data='search_song')],
                 [keyboards.menu]]))
            return

        CACHE[message.user.id] = {'search_results': results, 'search_page': 0}

        msg = ("🎵 <b>I found</b> <code>{songs}</code> <b>songs.</b>\n"
               "\n"
               "<i>Page</i> <code>{page}</code> <i>of</i> <code>{pages}</code><i>.</i>")

        msg = msg.format(songs=len(results), page=1, pages=len(
            [results[i:i + RESULTS_PER_PAGE] for i in range(0, len(results), RESULTS_PER_PAGE)]))

        user.set_back_status('search_page_' + str(CACHE[user.id]['search_page']))
        await to_delete.delete()
        await message.reply_text(msg, reply_markup=create_keyboard(results, 0, 'search_song'))

        search.add_to_history(message.user)


@Client.on_callback_query(filters.regex('^next_search_page$'))
async def on_next_search_page(_, callback):
    user = callback.user

    CACHE[callback.user.id]['search_page'] += 1

    msg = ("🎵 <b>I found</b> <code>{songs}</code> <b>songs.</b>\n"
           "\n"
           "<i>Page</i> <code>{page}</code> <i>of</i> <code>{pages}</code><i>.</i>")

    msg = msg.format(songs=len(CACHE[user.id]['search_results']), page=CACHE[user.id]['search_page'] + 1, pages=len(
        [CACHE[user.id]['search_results'][i:i + RESULTS_PER_PAGE] for i in
         range(0, len(CACHE[user.id]['search_results']), RESULTS_PER_PAGE)]))

    await callback.answer()
    await callback.edit_message_text(text=msg, reply_markup=
    create_keyboard(CACHE[user.id]['search_results'], CACHE[user.id]['search_page'],
                    'search_song'))

    user.set_back_status('search_page_' + str(CACHE[user.id]['search_page']))


@Client.on_callback_query(filters.regex('^search_page_'))
async def on_search_page(_, callback):
    user = callback.user

    CACHE[callback.user.id]['search_page'] = int(callback.data[len('search_page_'):])

    msg = ("🎵 <b>I found</b> <code>{songs}</code> <b>songs.</b>\n"
           "\n"
           "<i>Page</i> <code>{page}</code> <i>of</i> <code>{pages}</code><i>.</i>")

    msg = msg.format(songs=len(CACHE[user.id]['search_results']), page=CACHE[user.id]['search_page'] + 1, pages=len(
        [CACHE[user.id]['search_results'][i:i + RESULTS_PER_PAGE] for i in
         range(0, len(CACHE[user.id]['search_results']), RESULTS_PER_PAGE)]))

    await callback.answer()
    await callback.edit_message_text(text=msg, reply_markup=
    create_keyboard(CACHE[user.id]['search_results'], CACHE[user.id]['search_page'],
                    'search_song'))

    user.set_back_status('search_page_' + str(CACHE[user.id]['search_page']))


@Client.on_callback_query(filters.regex('^previous_search_page$'))
async def on_previous_search_page(_, callback):
    user = callback.user

    CACHE[user.id]['search_page'] -= 1

    msg = ("🎵 <b>I found</b> <code>{songs}</code> <b>songs.</b>\n"
           "\n"
           "<i>Page</i> <code>{page}</code> <i>of</i> <code>{pages}</code><i>.</i>")

    msg = msg.format(songs=len(CACHE[user.id]['search_results']), page=CACHE[user.id]['search_page'] + 1, pages=len(
        [CACHE[user.id]['search_results'][i:i + RESULTS_PER_PAGE] for i in
         range(0, len(CACHE[user.id]['search_results']), RESULTS_PER_PAGE)]))

    await callback.answer()
    await callback.edit_message_text(text=msg, reply_markup=
    create_keyboard(CACHE[user.id]['search_results'], CACHE[user.id]['search_page'],
                    'search_song'))

    user.set_back_status('search_page_' + str(CACHE[user.id]['search_page']))


def create_keyboard(results, page_num, back=None) -> InlineKeyboardMarkup:
    pages = [results[i:i + RESULTS_PER_PAGE] for i in range(0, len(results), RESULTS_PER_PAGE)]
    page = pages[page_num]

    keyboard = []

    for song in page:
        keyboard.append([InlineKeyboardButton(song.full_title, callback_data=f'song_{song.id}')])

    keyboard.append([])

    if page_num > 0:
        keyboard[-1].append(InlineKeyboardButton('⬅️', callback_data='previous_search_page'))

    if page_num < len(pages) - 1:
        keyboard[-1].append(InlineKeyboardButton('➡️', callback_data='next_search_page'))

    keyboard.append(keyboards.back_menu(back))

    return InlineKeyboardMarkup(keyboard)
