from pyrogram import Client, filters

from ..db.models import *

MESSAGE = ("<b>Lyrics</b> 🎵{banner}\n"
           "\n"
           "<i>Welcome to the bot,</i> {mention}<i>!</i>\n"
           "With this bot you can search any song and find <code>info</code>, <code>lyrics</code>, <code>artists</code> and much more!\n")

BANNER_URL = 'https://i.imgur.com/OO8vhWH.png'
BANNER_ENTITY = f"<a href='{BANNER_URL}'>{config.INVISIBLE_CHAR}</a>"

KEYBOARD = InlineKeyboardMarkup([[InlineKeyboardButton("Search 🔎", callback_data="search_song")],
                                 [InlineKeyboardButton("History 🕑", callback_data="history"),
                                  InlineKeyboardButton("Random 🎲", callback_data="random_song")],
                                 [InlineKeyboardButton("Info 📦", callback_data="info"),
                                  InlineKeyboardButton("Inline 🔗", switch_inline_query="")]])


@Client.on_message(filters.command(['start', 'menu']))
async def on_menu_message(_, message):
    with db_session:
        if len(message.command) > 1:
            arg = message.command[1].lower()

            if arg.startswith('song_'):
                song_id = int(arg[len('song_'):])
                song = Song.get(id=song_id)

                await message.reply_text(song.message(True), reply_markup=song.keyboard(message.user.back_status),
                                         disable_web_page_preview=False)
                message.user.set_back_status(f'song_{song.id}')

                song.add_to_history(message.user)

                return
            elif arg.startswith('lyrics_'):
                song_id = int(arg[len('lyrics_'):])
                song = Song.get(id=song_id)

                await message.reply_text(song.lyrics.message, reply_markup=song.lyrics.keyboard(f'song_{song.id}',
                                                                                                admin=message.user.is_admin))

                return
            elif arg.startswith('artists_'):
                song_id = int(arg[len('artists_'):])
                song = Song.get(id=song_id)

                msg = "👩‍🎤 <b>Artists of</b> {song}\n\n".format(song=song.deeplink)

                msg += "» {artist}\n".format(artist=song.artist.deeplink)

                for artist in song.featured_artists:
                    msg += "» {artist}\n".format(artist=artist.deeplink)

                await message.reply_text(msg,
                                         reply_markup=InlineKeyboardMarkup([keyboards.back_menu(f'song_{song.id}')]))

                return
            elif arg.startswith('producers_'):
                song_id = int(arg[len('producers_'):])
                song = Song.get(id=song_id)

                msg = "🧑🏻‍🔧 <b>Producers of</b> {song}\n\n".format(song=song.deeplink)

                for artist in song.producers:
                    msg += "» {artist}\n".format(artist=artist.deeplink)

                await message.reply_text(msg,
                                         reply_markup=InlineKeyboardMarkup([keyboards.back_menu(f'song_{song.id}')]))

                return
            elif arg.startswith('writers_'):
                song_id = int(arg[len('writers_'):])
                song = Song.get(id=song_id)

                msg = "🧑‍🎨 <b>Writers of</b> {song}\n\n".format(song=song.deeplink)

                for artist in song.writers:
                    msg += "» {artist}\n".format(artist=artist.deeplink)

                await message.reply_text(msg,
                                         reply_markup=InlineKeyboardMarkup([keyboards.back_menu(f'song_{song.id}')]))

                return
            elif arg.startswith('album_'):
                album_id = int(arg[len('album_'):])
                album = Album.get(id=album_id)

                await message.reply_text(album.message(True), reply_markup=album.keyboard(message.user.back_status),
                                         disable_web_page_preview=False)

                album.add_to_history(message.user)

                return
            elif arg.startswith('artist_'):
                artist_id = int(arg[len('artist_'):])
                artist = Artist.get(id=artist_id)

                await message.reply_text(artist.message(True),
                                         reply_markup=artist.keyboard(message.user.back_status),
                                         disable_web_page_preview=False)

                artist.add_to_history(message.user)

                return

        await message.reply_text(MESSAGE.format(banner=BANNER_ENTITY,
                                                mention=message.user.mention),
                                 reply_markup=KEYBOARD,
                                 disable_web_page_preview=False)

        message.user.reset_action()
        message.user.set_back_status('main_menu')


@Client.on_callback_query(filters.regex('^main_menu$'))
async def on_menu_callback(_, callback):
    await callback.answer()
    await callback.edit_message_text(MESSAGE.format(banner=BANNER_ENTITY,
                                                    mention=callback.user.mention),
                                     reply_markup=KEYBOARD,
                                     disable_web_page_preview=False)

    callback.user.reset_action()
    callback.user.set_back_status('main_menu')
