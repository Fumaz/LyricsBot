from pyrogram import Client, filters

from . import search
from ..db.models import *


@Client.on_callback_query(filters.regex('^song_'))
async def on_song(_, query):
    await query.answer()

    with db_session:
        song_id = int(query.data[len('song_'):])
        song = Song.get(id=song_id)

        back = query.user.back_status if not query.user.back_status.startswith(
            'song_') and not query.inline_message_id else None

        await query.edit_message_text(song.message(True),
                                      reply_markup=song.keyboard(back, menu=(not query.inline_message_id)),
                                      disable_web_page_preview=False)
        query.user.set_back_status(f'song_{song.id}')

        song.add_to_history(query.user)


@Client.on_callback_query(filters.regex('^lyrics_'))
async def on_lyrics(_, query):
    await query.answer()

    with db_session:
        song_id = int(query.data[len('lyrics_'):])
        song = Song.get(id=song_id)

        await query.edit_message_text(song.lyrics.message,
                                      reply_markup=song.lyrics.keyboard(f'song_{song.id}', admin=query.user.is_admin))


@Client.on_callback_query(filters.regex('^artists_'))
async def on_artists(_, query):
    await query.answer()

    with db_session:
        song_id = int(query.data[len('artists_'):])
        song = Song.get(id=song_id)

        msg = "👩‍🎤 <b>Artists of</b> {song}\n\n".format(song=song.deeplink)

        msg += "» {artist}\n".format(artist=song.artist.deeplink)

        for artist in song.featured_artists:
            msg += "» {artist}\n".format(artist=artist.deeplink)

        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[keyboards.back(f'song_{song.id}')]]),
                                      disable_web_page_preview=True)


@Client.on_callback_query(filters.regex('^producers_'))
async def on_producers(_, query):
    await query.answer()

    with db_session:
        song_id = int(query.data[len('producers_'):])
        song = Song.get(id=song_id)

        msg = "🧑🏻‍🔧 <b>Producers of</b> {song}\n\n".format(song=song.deeplink)

        for artist in song.producers:
            msg += "» {artist}\n".format(artist=artist.deeplink)

        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[keyboards.back(f'song_{song.id}')]]),
                                      disable_web_page_preview=True)


@Client.on_callback_query(filters.regex('^writers_'))
async def on_writers(_, query):
    await query.answer()

    with db_session:
        song_id = int(query.data[len('writers_'):])
        song = Song.get(id=song_id)

        msg = "🧑‍🎨 <b>Writers of</b> {song}\n\n".format(song=song.deeplink)

        for artist in song.writers:
            msg += "» {artist}\n".format(artist=artist.deeplink)

        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[keyboards.back(f'song_{song.id}')]]),
                                      disable_web_page_preview=True)


@Client.on_callback_query(filters.regex('^album_'))
async def on_album(_, query):
    await query.answer()

    with db_session:
        album_id = int(query.data[len('album_'):])
        album = Album.get(id=album_id)

        await query.edit_message_text(album.message(True), reply_markup=album.keyboard(query.user.back_status),
                                      disable_web_page_preview=False)

        album.add_to_history(query.user)


@Client.on_callback_query(filters.regex('^artist_'))
async def on_artist(_, query):
    await query.answer()

    with db_session:
        artist_id = int(query.data[len('artist_'):])
        artist = Artist.get(id=artist_id)

        await query.edit_message_text(artist.message(True), reply_markup=artist.keyboard(query.user.back_status),
                                      disable_web_page_preview=False)

        artist.add_to_history(query.user)


@Client.on_callback_query(filters.regex('^media_'))
async def on_media(_, query):
    await query.answer()

    with db_session:
        song_id = int(query.data[len('media_'):])
        song = Song.get(id=song_id)

        await query.edit_message_text(song.media_message(), reply_markup=song.media_keyboard(),
                                      disable_web_page_preview=True)


@Client.on_callback_query(filters.regex('^search_id_'))
async def on_search_id(_, query):
    await query.answer()

    with db_session:
        search_id = int(query.data[len('search_id_'):])
        search_db = Search.get(id=search_id)

        results = list(search_db.results)

        search.CACHE[query.user.id] = {'search_results': results, 'search_page': 0}

        msg = ("🎵 <b>I found</b> <code>{songs}</code> <b>songs.</b>\n"
               "\n"
               "<i>Page</i> <code>{page}</code> <i>of</i> <code>{pages}</code><i>.</i>")

        msg = msg.format(songs=len(results), page=1, pages=len(
            [results[i:i + search.RESULTS_PER_PAGE] for i in range(0, len(results), search.RESULTS_PER_PAGE)]))

        query.user.set_back_status('search_page_' + str(search.CACHE[query.user.id]['search_page']))
        await query.edit_message_text(msg, reply_markup=search.create_keyboard(results, 0, query.user.back_status))

        search_db.add_to_history(query.user)
