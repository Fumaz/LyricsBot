from pyrogram import Client, filters

from bot.db.models import *

CACHE = {}

MSG = ("<b>History</b> 🕑\n"
       "\n"
       "📆 <i>History size: </i><code>{history}</code>\n"
       "ℹ️ <i>Page</i> <code>{page}</code> <i>of</i> <code>{pages}</code><i>.</i>")

RESULTS_PER_PAGE = 5


@Client.on_message(filters.command('history'))
async def on_history_command(_, message):
    with db_session:
        user = message.user

        page = 0
        history = History.get_history(user)

        CACHE[user.id] = {'history': history, 'page': page}

        msg = create_message(history, page)
        keyboard = create_keyboard(history, page)

        await message.reply_text(text=msg, reply_markup=keyboard)

        user.set_back_status(f'history_page_{page}')


@Client.on_callback_query(filters.regex('^history$'))
async def on_history_callback(_, callback):
    with db_session:
        user = callback.user

        page = 0
        history = History.get_history(user)

        CACHE[callback.user.id] = {'history': history, 'page': page}

        msg = create_message(history, page)
        keyboard = create_keyboard(history, page)

        await callback.answer()
        await callback.edit_message_text(text=msg, reply_markup=keyboard)

        user.set_back_status(f'history_page_{page}')


@Client.on_callback_query(filters.regex('^history_page_'))
async def on_history_page(_, callback):
    user = callback.user

    page = int(callback.data[len('history_page_'):])
    history = CACHE[callback.user.id]['history']

    CACHE[callback.user.id]['page'] = page

    msg = MSG.format(history=len(history),
                     page=page + 1,
                     pages=len([history[i:i + RESULTS_PER_PAGE] for i in range(0, len(history), RESULTS_PER_PAGE)]))

    await callback.answer()
    await callback.edit_message_text(text=msg, reply_markup=create_keyboard(history, page))

    user.set_back_status(f'history_page_{page}')


def create_message(history, page):
    return MSG.format(history=len(history),
                      page=page + 1,
                      pages=len([history[i:i + RESULTS_PER_PAGE] for i in range(0, len(history), RESULTS_PER_PAGE)]))


def create_keyboard(results, page_num) -> InlineKeyboardMarkup:
    pages = [results[i:i + RESULTS_PER_PAGE] for i in range(0, len(results), RESULTS_PER_PAGE)]
    keyboard = []

    if len(pages) > page_num:
        page = pages[page_num]

        with db_session:
            for history in page:
                keyboard.append([history.button])

        keyboard.append([])

        if page_num > 0:
            keyboard[-1].append(InlineKeyboardButton('⬅️', callback_data=f'history_page_{page_num - 1}'))

        if page_num < len(pages) - 1:
            keyboard[-1].append(InlineKeyboardButton('➡️', callback_data=f'history_page_{page_num + 1}'))

    keyboard.append([keyboards.menu])

    return InlineKeyboardMarkup(keyboard)
