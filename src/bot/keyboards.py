from pyrogram.types import InlineKeyboardButton

from . import config

menu = InlineKeyboardButton(config.MENU, callback_data='main_menu')


def back(callback):
    return InlineKeyboardButton(config.BACK, callback_data=callback)


def back_menu(callback=None):
    l = []

    if callback and callback != 'main_menu':
        l.append(back(callback))

    l.append(menu)

    return l
