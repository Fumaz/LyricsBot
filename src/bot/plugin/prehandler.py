from pyrogram import Client

from .. import groups
from ..db.models import *


@Client.on_message(group=groups.PREHANDLER)
async def on_message(_, message):
    message.user = User.from_pyrogram(message)


@Client.on_inline_query(group=groups.PREHANDLER)
async def on_inline_query(_, query):
    query.user = User.from_pyrogram(query)


@Client.on_chosen_inline_result(group=groups.PREHANDLER)
async def on_chosen_inline_query(_, chosen):
    chosen.user = User.from_pyrogram(chosen)


@Client.on_callback_query(group=groups.PREHANDLER)
async def on_callback_query(_, query):
    query.user = User.from_pyrogram(query)


@Client.on_message(group=groups.BAN_CHECK)
async def on_message_ban_check(_, message):
    if message.user.is_banned:
        message.stop_propagation()


@Client.on_callback_query(group=groups.BAN_CHECK)
async def on_callback_ban_check(_, callback):
    if callback.user.is_banned:
        callback.stop_propagation()


@Client.on_inline_query(group=groups.BAN_CHECK)
async def on_inline_query_ban_check(_, query):
    if query.user.is_banned:
        query.stop_propagation()
