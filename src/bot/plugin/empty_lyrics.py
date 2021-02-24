from datetime import timedelta

from pyrogram import Client, filters

from bot import tfilters, paste, genius
from bot.db.models import *

DELAY = timedelta(days=1)

REQUEST_MESSAGE = ("<b>New Request!</b> 🔔\n"
                   "\n"
                   "👤 User » {mention}\n"
                   "🎵 Song » {song}\n"
                   "\n"
                   "📅 Date » <code>{date}</code>")

SUGGESTION_MESSAGE = ("<b>New Suggestion!</b> 🔔\n"
                      "\n"
                      "👤 User » {mention}\n"
                      "🎵 Song » {song}\n"
                      "\n"
                      "💬 Text » <code>{text}</code>")

REQUEST_CHANNEL_ID = -1001397050768


@Client.on_callback_query(filters.regex('^request_lyrics_'))
async def on_request_lyrics(client, callback):
    with db_session:
        user = callback.user.current
        song_id = int(callback.data[len('request_lyrics_'):])
        song = Song.get(id=song_id)

        if song.lyrics.text != config.LYRICS_NOT_FOUND:
            await callback.answer('❌ This song already has lyrics.', show_alert=True)
        else:
            request = LyricsRequest.select(lambda r: r.user == user and r.song == song).order_by(
                lambda r: desc(r.creation_date))

            if len(request) > 0 and request[:][0].creation_date > datetime.now() - DELAY:
                await callback.answer('❌ You already sent a request for this song.', show_alert=True)
            else:
                await callback.answer('✅ Request sent!', show_alert=True)

                request = LyricsRequest(user=user, song=song)
                commit()

                message = REQUEST_MESSAGE.format(mention=request.user.mention,
                                                 song=request.song.deeplink,
                                                 date=request.creation_date)

                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("View Online 🌐", url=request.song.lyrics.url)],
                                                 [InlineKeyboardButton("Accept ✅",
                                                                       callback_data=f"accept_request_{request.id}"),
                                                  InlineKeyboardButton("Deny ❌",
                                                                       callback_data=f"deny_request_{request.id}")],
                                                 [InlineKeyboardButton("Ban User ⛔️",
                                                                       callback_data=f"ban_{request.user.id}")]])

                await client.send_message(REQUEST_CHANNEL_ID, message, reply_markup=keyboard,
                                          disable_web_page_preview=True)


@Client.on_callback_query(filters.regex('^suggest_lyrics_'))
async def on_suggest_lyrics(_, callback):
    with db_session:
        user = callback.user.current
        song_id = int(callback.data[len('suggest_lyrics_'):])
        song = Song.get(id=song_id)

        suggestion = LyricsSuggestion.select(lambda s: s.user == user and s.song == song).order_by(
            lambda s: desc(s.creation_date))

        if len(suggestion) > 0 and suggestion[:][0].creation_date > datetime.now() - DELAY:
            await callback.answer('❌ You already sent a suggestion for this song.', show_alert=True)
        else:
            user.set_action(f'suggest_lyrics_{song.id}')

            await callback.answer()
            await callback.edit_message_text('💭 <b>Now type the lyrics of the song (or your suggestion).</b>',
                                             reply_markup=InlineKeyboardMarkup([[keyboards.back(f'lyrics_{song.id}')]]))


@Client.on_message(tfilters.action_startswith('suggest_lyrics_') & filters.text)
async def on_suggest_lyrics_text(client, message):
    if message.text.startswith('/'):
        return

    with db_session:
        user = message.user.current

        song_id = int(user.action[len('suggest_lyrics_'):])
        song = Song.get(id=song_id)

        user.reset_action()
        suggestion = LyricsSuggestion(user=user, song=song, suggestion=message.text)
        commit()

        await message.reply_text('✅ <b>Thanks for your suggestion.</b>',
                                 reply_markup=InlineKeyboardMarkup([keyboards.back_menu(f'lyrics_{song.id}')]))

        msg = SUGGESTION_MESSAGE.format(mention=suggestion.user.mention,
                                        song=suggestion.song.deeplink,
                                        text=suggestion.suggestion)

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("View Online 🌐", url=suggestion.song.lyrics.url)],
                                         [InlineKeyboardButton("Accept ✅",
                                                               callback_data=f"accept_suggestion_{suggestion.id}"),
                                          InlineKeyboardButton("Deny ❌",
                                                               callback_data=f"deny_suggestion_{suggestion.id}")],
                                         [InlineKeyboardButton("Ban User ⛔️",
                                                               callback_data=f"ban_{suggestion.user.id}")]])

        await client.send_message(REQUEST_CHANNEL_ID, msg, reply_markup=keyboard,
                                  disable_web_page_preview=True)


@Client.on_callback_query(filters.regex('^accept_request_') & tfilters.admin())
async def on_accept_request(client, callback):
    print(callback.data)
    with db_session:
        request_id = int(callback.data[len('accept_request_'):])
        request = LyricsRequest.get(id=request_id)

        request.status = 'accepted'

        await callback.answer()
        await callback.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("Accepted ✅", callback_data="none")]]))

        try:
            await client.send_message(request.user.id,
                                      '✅ <b>Your lyrics request for</b> {song} <b>has been accepted!</b>'.format(
                                          song=request.song.deeplink),
                                      disable_web_page_preview=True)
        except:
            pass


@Client.on_callback_query(filters.regex('^deny_request_') & tfilters.admin())
async def on_deny_request(client, callback):
    print(callback.data)
    with db_session:
        request_id = int(callback.data[len('deny_request_'):])
        request = LyricsRequest.get(id=request_id)

        request.status = 'denied'

        await callback.answer()
        await callback.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("Denied ❌", callback_data="none")]]))

        try:
            await client.send_message(request.user.id,
                                      '❌ <b>Your lyrics request for</b> {song} <b>has been denied!</b>'.format(
                                          song=request.song.deeplink),
                                      disable_web_page_preview=True)
        except:
            pass


@Client.on_callback_query(filters.regex('^accept_suggestion_') & tfilters.admin())
async def on_accept_suggestion(client, callback):
    print(callback.data)
    with db_session:
        suggestion_id = int(callback.data[len('accept_suggestion_'):])
        suggestion = LyricsSuggestion.get(id=suggestion_id)

        suggestion.status = 'accepted'

        await callback.answer()
        await callback.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("Accepted ✅", callback_data="none")]]))

        try:
            await client.send_message(suggestion.user.id,
                                      '✅ <b>Your lyrics suggestion for</b> {song} <b>has been accepted!</b>'.format(
                                          song=suggestion.song.deeplink),
                                      disable_web_page_preview=True)
        except:
            pass


@Client.on_callback_query(filters.regex('^deny_suggestion_') & tfilters.admin())
async def on_deny_suggestion(client, callback):
    print(callback.data)
    with db_session:
        suggestion_id = int(callback.data[len('deny_suggestion_'):])
        suggestion = LyricsSuggestion.get(id=suggestion_id)

        suggestion.status = 'denied'

        await callback.answer()
        await callback.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("Denied ❌", callback_data="none")]]))

        try:
            await client.send_message(suggestion.user.id,
                                      '❌ <b>Your lyrics suggestion for</b> {song} <b>has been denied!</b>'.format(
                                          song=suggestion.song.deeplink),
                                      disable_web_page_preview=True)
        except:
            pass


@Client.on_callback_query(filters.regex('^set_lyrics_') & tfilters.admin())
async def on_set_lyrics(_, callback):
    user = callback.user

    with db_session:
        song_id = int(callback.data[len('set_lyrics_'):])
        song = Song.get(id=song_id)
        user.set_action(f'set_lyrics_{song_id}')

        await callback.answer()
        await callback.edit_message_text('💭 <b>Now send the new lyrics.</b>',
                                         reply_markup=InlineKeyboardMarkup(
                                             [[InlineKeyboardButton("View Online 🌐", url=song.lyrics.url),
                                               InlineKeyboardButton("Raw Data 🧬",
                                                                    url=f'https://genius.com/songs/{song.genius_id}/embed.js')],
                                              keyboards.back_menu(f'lyrics_{song_id}')]))


@Client.on_message(tfilters.action_startswith('set_lyrics_') & tfilters.admin() & filters.text)
async def on_set_lyrics_text(_, message):
    user = message.user
    user.reset_action()

    with db_session:
        song_id = int(user.action[len('set_lyrics_'):])
        song = Song.get(id=song_id)

        if message.text.startswith('http') or '.com/' in message.text:
            text = paste.from_url(message.text)

            if 'document.write(JSON.parse(' in text:
                text = genius.api.genius_from_text(text)
        else:
            text = message.text

        song.lyrics.text = text
        song.lyrics.telegraph_url = ''

        await message.reply_text('✅ <b>Done!</b>',
                                 reply_markup=InlineKeyboardMarkup([keyboards.back_menu(f'lyrics_{song.id}')]))


@Client.on_message(filters.command('setlyrics') & tfilters.admin())
async def on_set_lyrics_command(_, message):
    user = message.user

    with db_session:
        arg = ' '.join(message.command[1:])

        try:
            song_id = int(arg)
            song = Song.get(id=song_id)
        except:
            song = Song.select(lambda s: arg.lower() in s.title.lower())

            if len(song) < 1:
                await message.reply_text('Song not found.')
            else:
                song = song[:][0]

        user.set_action(f'set_lyrics_{song.id}')
        await message.reply_text('💭 <b>Now send the new lyrics for</b> {song}<b>.</b>'.format(song=song.deeplink),
                                 reply_markup=InlineKeyboardMarkup(
                                     [[InlineKeyboardButton("View Online 🌐", url=song.lyrics.url),
                                       InlineKeyboardButton("Raw Data 🧬",
                                                            url=f'https://genius.com/songs/{song.genius_id}/embed.js')]]))
