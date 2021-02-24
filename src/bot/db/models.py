from datetime import datetime, date
from typing import Union, List

from pony.orm import *
from pyrogram import types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import config
from bot import keyboards

db = Database()


class User(db.Entity):
    id = PrimaryKey(int)
    first_name = Required(str)
    last_name = Optional(str)
    username = Optional(str)
    language = Required(str)
    is_active = Required(bool, default=True)
    is_admin = Required(bool, default=False)
    is_banned = Required(bool, default=False)
    action = Optional(str, default='')
    back_status = Optional(str, default='')
    start_reason = Required(str)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)

    searches = Set('Search')
    history = Set('History')
    requests = Set('LyricsRequest')
    suggestions = Set('LyricsSuggestion')

    @staticmethod
    @db_session
    def from_pyrogram(tg_user: Union[types.User, types.Message,
                                     types.InlineQuery, types.CallbackQuery,
                                     types.ChosenInlineResult]) -> 'User':
        start_reason = 'unknown'

        if isinstance(tg_user, types.Message):
            start_reason = 'message'
            tg_user = tg_user.from_user
        elif isinstance(tg_user, types.InlineQuery):
            start_reason = 'inline'
            tg_user = tg_user.from_user
        elif isinstance(tg_user, types.CallbackQuery):
            start_reason = 'callback'
            tg_user = tg_user.from_user
        elif isinstance(tg_user, types.ChosenInlineResult):
            start_reason = 'chosen_inline'
            tg_user = tg_user.from_user

        id = tg_user.id
        first_name = tg_user.first_name
        last_name = tg_user.last_name or ''
        username = tg_user.username or ''
        language = tg_user.language_code.lower()[:2] if tg_user.language_code else 'unknown'

        db_user = User.get(id=id)

        if not db_user:
            db_user = User(id=id,
                           first_name=first_name,
                           last_name=last_name,
                           username=username,
                           language=language,
                           start_reason=start_reason)
        else:
            db_user.is_active = True
            db_user.first_name = first_name
            db_user.last_name = last_name
            db_user.username = username
            db_user.last_update = datetime.now()
            db_user.language = language

        db_user.tg = tg_user

        return db_user

    @property
    def full_name(self) -> str:
        return f'{self.first_name}{" " + self.last_name if self.last_name else ""}'

    @property
    def mention(self) -> str:
        return f"<a href='tg://user?id={self.id}'>{self.first_name}</a>"

    @property
    def current(self) -> 'User':
        return User.get(id=self.id)

    @db_session
    def set_action(self, action: str) -> 'User':
        self = self.current

        self.action = action
        return self

    @db_session
    def reset_action(self) -> 'User':
        self = self.current

        self.action = ''
        return self

    @db_session
    def set_back_status(self, back: str) -> 'User':
        self = self.current

        self.back_status = back
        return self

    @db_session
    def reset_back_status(self) -> 'User':
        self = self.current

        self.back_status = ''
        return self


class Search(db.Entity):
    id = PrimaryKey(int, auto=True)
    user = Optional(User)
    query = Required(str)
    type = Required(str)
    creation_time = Required(datetime, default=datetime.now)

    results = Set('Song')
    history = Set('History')

    @staticmethod
    @db_session
    def from_json(user: User, query: str, data: dict, type: str) -> 'Search':
        user = user.current
        songs = [Song.from_json(song) for song in data]

        return Search(user=user, query=query, results=songs, type=type)

    @staticmethod
    def total_searched_songs() -> int:
        return sum([len(search.results) for search in Search.select()])

    @staticmethod
    def from_cache(query: str) -> 'Search':
        searches = Search.select(lambda s: s.query.lower() == query.lower()).order_by(lambda s: desc(s.creation_time))

        if len(searches) > 0:
            return searches[:][0]
        else:
            return None

    @db_session
    def add_to_history(self, user: User):
        self = Search.get(id=self.id)

        return History(user=user.current, search=self)


class Song(db.Entity):
    id = PrimaryKey(int, auto=True)
    genius_id = Required(int)
    release_date = Optional(date)
    title = Required(str)
    full_title = Required(str)
    title_with_featured = Required(str)
    lyrics = Optional('Lyrics')
    art = Optional('Art')
    header = Optional('Header')
    stats = Optional('Stats')
    apple = Optional('AppleMusic')
    album = Optional('Album')
    artist = Required('Artist')
    scraped = Required(bool, default=False)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)

    featured_artists = Set('Artist')
    producers = Set('Artist')
    writers = Set('Artist')
    media = Set('Media')
    relationships = Set('Relationship')
    in_relationships = Set('Relationship')
    searches = Set('Search')
    history = Set('History')
    queries = Set('Queries')
    requests = Set('LyricsRequest')
    suggestions = Set('LyricsSuggestion')

    @staticmethod
    def from_json(data: dict, update: bool = False) -> 'Song':
        genius_id = data['id']

        song = Song.get(genius_id=genius_id)

        if not song or update:
            title = data['title']
            full_title = data['full_title']
            title_with_featured = data['title_with_featured']
            lyrics_text = data['lyrics'] if 'lyrics' in data else ''
            artist = Artist.from_json(data['primary_artist'])

            if not song:
                song = Song(genius_id=genius_id,
                            release_date=None,
                            title=title,
                            full_title=full_title,
                            title_with_featured=title_with_featured,
                            artist=artist,
                            featured_artists=[],
                            producers=[],
                            writers=[])

            lyrics = Lyrics.from_json(song, data, lyrics_text)
            art = Art.from_json(song, data)
            header = Header.from_json(song, data)

            song.lyrics = lyrics
            song.art = art
            song.header = header

        return song

    @db_session
    def update(self) -> 'Song':
        from bot import genius

        if self.scraped:
            return self

        song = Song.get(id=self.id)
        data = genius.api.song(song.genius_id)

        album = None
        if 'album' in data and data['album']:
            album = Album.from_json(data['album'])

        song.stats = Stats.from_json(song, data, True)
        song.release_date = data['release_date']
        song.featured_artists = [Artist.from_json(featured) for featured in
                                 data['featured_artists']] if 'featured_artists' in data else []
        song.producers = [Artist.from_json(producer) for producer in
                          data['producer_artists']] if 'producer_artists' in data else []
        song.writers = [Artist.from_json(writer) for writer in
                        data['writer_artists']] if 'writer_artists' in data else []
        song.apple = AppleMusic.from_json(song, data) if 'apple_music_id' in data and data['apple_music_id'] else None
        song.media = [Media.from_json(song, d) for d in data['media']] if 'media' in data else []
        song.relationships = [Relationship.from_json(song, d) for d in
                              data['song_relationships']] if 'song_relationships' in data else []

        if album:
            song.album = album

        song.scraped = True

        return song

    @property
    def deeplink(self) -> str:
        return f"<a href='{config.DEEP_LINKING}song_{self.id}'>{self.title}</a>"

    def message(self, image: bool = False) -> str:
        if not self.scraped:
            self = self.update()

        return ("<b>{title}</b> 🎵{image}\n"
                "\n"
                "👩‍🎤 Artist » {artist}\n"
                "📅 Release date » <code>{release_date}</code>{album}").format(title=self.title,
                                                                               artist=self.artist.deeplink,
                                                                               release_date=self.release_date,
                                                                               album=f"\n\n🎶 Album » {self.album.deeplink}" if self.album else "",
                                                                               image=f"<a href='{self.thumbnail}'>{config.INVISIBLE_CHAR}</a>" if image and self.thumbnail else "")

    def keyboard(self, back=None, menu=True) -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton('View online 🌐', url=self.lyrics.url)], []]

        if len(self.producers) > 0:
            keyboard[-1].append(InlineKeyboardButton('Producers 🧑🏻‍🔧', callback_data=f'producers_{self.id}'))
        if len(self.writers) > 0:
            keyboard[-1].append(InlineKeyboardButton('Writers 🧑‍🎨', callback_data=f'writers_{self.id}'))

        keyboard[-1].append(InlineKeyboardButton('Artists 👩‍🎤', callback_data=f'artists_{self.id}'))

        keyboard.append([])

        keyboard[-1].append(InlineKeyboardButton('Lyrics 📑', callback_data=f'lyrics_{self.id}'))

        if self.album:
            keyboard[-1].append(InlineKeyboardButton('Album 💽', callback_data=f'album_{self.album.id}'))

        keyboard[-1].append(InlineKeyboardButton('Media 🦠', callback_data=f'media_{self.id}'))

        if menu:
            keyboard.append(keyboards.back_menu(back))

        return InlineKeyboardMarkup(keyboard)

    def media_message(self) -> str:
        msg = "<b>Media</b> 🦠\n\n"

        for media in self.media:
            msg += f"» {media.deeplink}\n"

        return msg

    def media_keyboard(self) -> InlineKeyboardMarkup:
        medias = self.media
        keyboard = [[]]

        for media in medias:
            if len(keyboard[-1]) > 3:
                keyboard[-1].append([])

            keyboard[-1].append(media.button)

        keyboard.append([keyboards.back(f'song_{self.id}')])

        return InlineKeyboardMarkup(keyboard)

    @property
    def thumbnail(self) -> str:
        if self.art and self.art.thumbnail_url:
            return self.art.thumbnail_url
        elif self.header and self.header.thumbnail_url:
            return self.header.thumbnail_url

        return None

    @db_session
    def add_to_history(self, user: User):
        self = Song.get(id=self.id)

        return History(user=user.current, song=self)

    @property
    def button(self) -> InlineKeyboardButton:
        return InlineKeyboardButton(self.full_title, callback_data=f'song_{self.id}')


class Lyrics(db.Entity):
    song = PrimaryKey(Song)
    owner_id = Optional(int)
    placeholder_reason = Optional(str)
    state = Optional(str)
    url = Required(str)
    text = Optional(str)
    telegraph_url = Optional(str)

    @staticmethod
    def from_json(song: Song, data: dict, text: str = '') -> 'Lyrics':
        lyrics = Lyrics.get(song=song)

        if not lyrics:
            owner_id = data['lyrics_owner_id'] if 'lyrics_owner_id' in data else ''
            placeholder_reason = data['lyrics_placeholder_reason'] if 'lyrics_placeholder_reason' in data else ''
            state = data['lyrics_state'] if 'state' in data else ''
            url = data['url']

            lyrics = Lyrics(song=song,
                            owner_id=owner_id,
                            placeholder_reason=placeholder_reason,
                            state=state,
                            url=url,
                            text=text)
        elif text:
            lyrics.text = text

        return lyrics

    @property
    def message(self) -> str:
        if not self.text:
            self = self.update()

        return ("<b>{title}</b> 🎵\n"
                "\n"
                "{lyrics}").format(title=self.song.full_title or self.song.title,
                                   lyrics=f'<code>{self.text}</code>' if len(
                                       self.text) < 4000 else self.telegraph)

    def keyboard(self, back=None, admin=False) -> InlineKeyboardMarkup:
        if self.text and self.text != config.LYRICS_NOT_FOUND:
            return InlineKeyboardMarkup(
                [[InlineKeyboardButton('View online 🌐', url=self.telegraph)], [keyboards.back(back)]])
        else:
            if admin:
                return InlineKeyboardMarkup([[InlineKeyboardButton("View Online 🌐", url=self.song.lyrics.url)],
                                             [InlineKeyboardButton("Add Lyrics ✅",
                                                                   callback_data=f"set_lyrics_{self.song.id}")],
                                             [InlineKeyboardButton("Refresh 🔄",
                                                                   callback_data=f"lyrics_{self.song.id}")],
                                             [keyboards.back(back)]])
            else:
                return InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Request 🔑", callback_data=f"request_lyrics_{self.song.id}"),
                      InlineKeyboardButton("Suggest 🎈", callback_data=f"suggest_lyrics_{self.song.id}")],
                     [InlineKeyboardButton("Refresh 🔄", callback_data=f"lyrics_{self.song.id}")],
                     [keyboards.back(back)]]
                )

    @db_session
    def update(self) -> 'Lyrics':
        from bot import genius

        text = genius.lyrics(self.song)

        if not text:
            text = config.LYRICS_NOT_FOUND

        lyrics = Lyrics.get(song=self.song)
        lyrics.text = text.replace('\n\n', '\n')

        return lyrics

    @property
    @db_session
    def telegraph(self) -> str:
        if self.telegraph_url:
            return self.telegraph_url

        if not self.text:
            lyrics = self.update()
        else:
            lyrics = self

        response = config.TELEGRAPH.create_page(title=self.song.full_title or self.song.title,
                                                author_name='Lyrics',
                                                author_url='https://t.me/' + config.BOT_USERNAME,
                                                html_content=self.text.replace('\n', '<br>'))

        lyrics.telegraph_url = 'https://telegra.ph/' + response['path']
        return lyrics.telegraph_url


class Art(db.Entity):
    song = PrimaryKey(Song)
    thumbnail_url = Optional(str)
    image_url = Optional(str)

    @staticmethod
    def from_json(song: Song, data: dict) -> 'Art':
        art = Art.get(song=song)

        if not art:
            thumbnail_url = data['song_art_image_thumbnail_url']
            image_url = data['song_art_image_url']

            art = Art(song=song, thumbnail_url=thumbnail_url, image_url=image_url)

        return art


class Header(db.Entity):
    song = PrimaryKey(Song)
    thumbnail_url = Optional(str)
    image_url = Optional(str)

    @staticmethod
    def from_json(song: Song, data: dict) -> 'Header':
        header = Header.get(song=song)

        if not header:
            thumbnail_url = data['header_image_thumbnail_url']
            image_url = data['header_image_url']

            header = Header(song=song, thumbnail_url=thumbnail_url, image_url=image_url)

        return header


class Stats(db.Entity):
    song = PrimaryKey(Song)
    annotation_count = Optional(int)
    accepted_annotations = Optional(int)
    contributors = Optional(int)
    iq_earners = Optional(int)
    transcribers = Optional(int)
    unreviewed_annotations = Optional(int)
    verified_annotations = Optional(int)
    hot = Optional(bool)
    page_views = Optional(int)

    @staticmethod
    def from_json(song: Song, data: dict, update: bool = False) -> 'Stats':
        stats = Stats.get(song=song)

        if not stats or update:
            annotation_count = data['annotation_count']
            accepted_annotations = None
            contributors = None
            iq_earners = None
            transcribers = None
            unreviewed_annotations = None
            verified_annotations = None
            hot = None
            page_views = None

            if 'stats' in data:
                accepted_annotations = data['stats']['accepted_annotations'] if 'accepted_annotations' in data else None
                contributors = data['stats']['contributors'] if 'contributors' in data else None
                iq_earners = data['stats']['iq_earners'] if 'iq_earners' in data else None
                transcribers = data['stats']['transcribers'] if 'transcribers' in data else None
                unreviewed_annotations = data['stats'][
                    'unreviewed_annotations'] if 'unreviewed_annotations' in data else None
                hot = data['stats']['hot'] if 'hot' in data else None
                page_views = data['stats']['pageviews'] if 'pageviews' in data else None
                verified_annotations = data['stats']['verified_annotations'] if 'verified_annotations' in data else None

            if not stats:
                stats = Stats(song=song,
                              annotation_count=annotation_count,
                              accepted_annotations=accepted_annotations,
                              contributors=contributors,
                              iq_earners=iq_earners,
                              transcribers=transcribers,
                              unreviewed_annotations=unreviewed_annotations,
                              verified_annotations=verified_annotations,
                              hot=hot,
                              page_views=page_views)
            else:
                stats.annotation_count = annotation_count
                stats.accepted_annotations = accepted_annotations
                stats.contributors = contributors
                stats.iq_earners = iq_earners
                stats.transcribers = transcribers
                stats.unreviewed_annotations = unreviewed_annotations
                stats.verified_annotations = verified_annotations
                stats.hot = hot
                stats.page_views = page_views

        return stats


class AppleMusic(db.Entity):
    song = PrimaryKey(Song)
    music_id = Optional(str)
    player_url = Optional(str)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)

    @staticmethod
    def from_json(song: Song, data: dict) -> 'AppleMusic':
        apple = AppleMusic.get(song=song)

        if not apple:
            music_id = data['apple_music_id']
            player_url = data['apple_music_player_url']

            apple = AppleMusic(song=song, music_id=music_id, player_url=player_url)

        return apple


class Album(db.Entity):
    id = PrimaryKey(int, auto=True)
    genius_id = Required(int)
    title = Required(str)
    full_title = Required(str)
    url = Required(str)
    cover_art_url = Required(str)
    release_date = Optional(date)
    views = Optional(int)
    comment_count = Optional(int)
    scraped = Required(bool, default=False)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)

    artist = Required('Artist')
    songs = Set(Song)
    history = Set('History')

    @staticmethod
    def from_json(data: dict) -> 'Album':
        album = Album.get(genius_id=data['id'])

        if not album:
            genius_id = data['id']
            title = data['name']
            full_title = data['full_title']
            url = data['url']
            cover_art_url = data['cover_art_url']
            artist = Artist.from_json(data['artist'])

            album = Album(genius_id=genius_id,
                          title=title,
                          full_title=full_title,
                          url=url,
                          cover_art_url=cover_art_url,
                          artist=artist)

        return album

    def message(self, image: bool = False) -> str:
        if not self.scraped:
            self = self.update()

        return ("<b>{title}</b> 💽{image}\n"
                "\n"
                "👩‍🎤 Artist » {artist}\n"
                "📅 Release date » <code>{release_date}</code>\n"
                "\n"
                "👁 Views » <code>{views}</code>\n"
                "💬 Comments » <code>{comment_count}</code>").format(title=self.title,
                                                                     artist=self.artist.deeplink,
                                                                     release_date=self.release_date,
                                                                     views=self.views,
                                                                     comment_count=self.comment_count,
                                                                     image=f"<a href='{self.cover_art_url}'>{config.INVISIBLE_CHAR}</a>" if image else '')

    def keyboard(self, back=None) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton('View online 🌐', url=self.url)], [keyboards.back(back)]])

    @property
    def deeplink(self) -> str:
        return f"<a href='{config.DEEP_LINKING}album_{self.id}'>{self.title}</a>"

    @db_session
    def update(self, force: bool = False) -> 'Album':
        if self.scraped and not force:
            return self

        from bot import genius

        self = Album.get(id=self.id)
        result = genius.api.album(self.genius_id)

        self.release_date = result['release_date']
        self.views = result['song_pageviews']
        self.comment_count = result['comment_count']
        self.scraped = True

        return self

    @db_session
    def add_to_history(self, user: User):
        self = Album.get(id=self.id)

        return History(user=user.current, album=self)


class Artist(db.Entity):
    id = PrimaryKey(int, auto=True)
    genius_id = Required(int)
    name = Required(str)
    url = Required(str)
    iq = Required(int)
    image_url = Required(str)
    header_image_url = Required(str)
    is_meme_verified = Required(bool)
    is_verified = Required(bool)
    facebook = Optional(str, default='')
    instagram = Optional(str, default='')
    twitter = Optional(str, default='')
    followers = Optional(int)
    alternate_names = Optional(StrArray)
    scraped = Required(bool, default=False)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)

    albums = Set(Album)
    songs = Set(Song, reverse='artist')
    featured_in = Set(Song, reverse='featured_artists')
    producer_in = Set(Song, reverse='producers')
    writer_in = Set(Song, reverse='writers')
    history = Set('History')

    @staticmethod
    def from_json(data: dict) -> 'Artist':
        artist = Artist.get(genius_id=data['id'])

        if not artist:
            genius_id = data['id']
            name = data['name']
            url = data['url']
            iq = data['iq'] if 'iq' in data else 0
            image_url = data['image_url']
            header_image_url = data['header_image_url']
            is_meme_verified = data['is_meme_verified']
            is_verified = data['is_verified']

            artist = Artist(genius_id=genius_id,
                            name=name,
                            url=url,
                            iq=iq,
                            image_url=image_url,
                            header_image_url=header_image_url,
                            is_meme_verified=is_meme_verified,
                            is_verified=is_verified)

        return artist

    def message(self, image: bool = False) -> str:
        if not self.scraped:
            self = self.update()

        msg = "<b>{name}</b> 👩‍🎤".format(name=self.name)

        if image:
            msg += f"<a href='{self.image_url}'>{config.INVISIBLE_CHAR}</a>"

        msg += "\n\n"

        if self.facebook:
            msg += "📬 Facebook » <a href='{facebook_url}'>{facebook_name}</a>\n".format(facebook_url=self.facebook_url,
                                                                                         facebook_name=self.facebook)
        if self.instagram:
            msg += "📸 Instagram » <a href='{instagram_url}'>{instagram_name}</a>\n".format(
                instagram_url=self.instagram_url,
                instagram_name=self.instagram)
        if self.twitter:
            msg += "🐣 Twitter » <a href='{twitter_url}'>{twitter_name}</a>\n".format(twitter_url=self.twitter_url,
                                                                                      twitter_name=self.twitter)

        if not msg.endswith('\n\n'):
            msg += '\n'

        msg += ("👥 Followers » <code>{followers}</code>\n"
                "👤 Alternate Names » <code>{alternate_names}</code>").format(followers=self.followers,
                                                                              alternate_names=', '.join(
                                                                                  self.alternate_names) or 'None')

        return msg

    def keyboard(self, back=None) -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton('View online 🌐', url=self.url)], []]

        if self.facebook:
            keyboard[-1].append(InlineKeyboardButton('📬 FB', url=self.facebook_url))
        if self.instagram:
            keyboard[-1].append(InlineKeyboardButton('📸 IG', url=self.instagram_url))
        if self.twitter:
            keyboard[-1].append(InlineKeyboardButton('🐣 TWT', url=self.twitter_url))

        keyboard.append([keyboards.back(back)])

        return InlineKeyboardMarkup(keyboard)

    @property
    def deeplink(self) -> str:
        return f"<a href='{config.DEEP_LINKING}artist_{self.id}'>{self.name}</a>"

    @property
    def facebook_url(self) -> str:
        return f"https://facebook.com/{self.facebook}"

    @property
    def instagram_url(self) -> str:
        return f"https://instagram.com/{self.instagram}"

    @property
    def twitter_url(self) -> str:
        return f"https://twitter.com/{self.twitter}"

    @db_session
    def update(self, force: bool = False) -> 'Artist':
        if self.scraped and not force:
            return self

        from bot import genius

        self = Artist.get(id=self.id)
        result = genius.api.artist(self.genius_id)

        self.facebook = result['facebook_name'] or '' if 'facebook_name' in result else ''
        self.instagram = result['instagram_name'] or '' if 'instagram_name' in result else ''
        self.twitter = result['twitter_name'] or '' if 'twitter_name' in result else ''
        self.followers = result['followers_count'] or 0 if 'followers_count' in result else 0
        self.alternate_names = result['alternate_names'] or [] if 'alternate_names' in result else []
        self.iq = result['iq'] or 0 if 'iq' in result else 0
        self.scraped = True

        return self

    @db_session
    def add_to_history(self, user: User):
        self = Artist.get(id=self.id)

        return History(user=user.current, artist=self)


class Media(db.Entity):
    url = PrimaryKey(str)
    provider = Required(str)
    type = Required(str)
    song = Required(Song)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)

    @staticmethod
    def from_json(song: Song, data: dict) -> 'Media':
        media = Media.get(url=data['url'])

        if not media:
            url = data['url']
            provider = data['provider']
            type = data['type']

            media = Media(url=url,
                          provider=provider,
                          type=type,
                          song=song)

        return media

    @property
    def deeplink(self) -> str:
        return f"<a href='{self.url}'>{self.provider.capitalize()}</a>"

    @property
    def button(self) -> InlineKeyboardButton:
        return InlineKeyboardButton(self.provider.capitalize(), url=self.url)


class Relationship(db.Entity):
    id = PrimaryKey(int, auto=True)
    song = Required(Song, reverse='relationships')
    relationship_type = Required(str)
    type = Required(str)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)

    songs = Set(Song, reverse='in_relationships')

    @staticmethod
    def from_json(song: Song, data: dict) -> 'Relationship':
        relationship_type = data['relationship_type']
        type = data['type']

        relationship = Relationship.select(
            lambda r: r.song == song and r.relationship_type == relationship_type and r.type == type)

        if len(relationship) < 1:
            songs = [Song.from_json(song) for song in data['songs']]

            relationship = Relationship(song=song,
                                        relationship_type=relationship_type,
                                        type=type,
                                        songs=songs)
        else:
            relationship = relationship[:][0]

        return relationship


class History(db.Entity):
    id = PrimaryKey(int, auto=True)
    user = Required(User)
    song = Optional(Song)
    album = Optional(Album)
    artist = Optional(Artist)
    search = Optional(Search)
    creation_date = Required(datetime, default=datetime.now)

    @property
    def button(self) -> InlineKeyboardButton:
        self = History.get(id=self.id)

        if self.song:
            return InlineKeyboardButton(self.song.full_title + ' 🎵', callback_data=f'song_{self.song.id}')
        elif self.album:
            return InlineKeyboardButton(self.album.full_title + ' 💽', callback_data=f'album_{self.album.id}')
        elif self.artist:
            return InlineKeyboardButton(self.artist.name + ' 👩‍🎤', callback_data=f'artist_{self.artist.id}')
        elif self.search:
            return InlineKeyboardButton(self.search.query + ' 🔎', callback_data=f'search_id_{self.search.id}')

        return None

    @staticmethod
    @db_session
    def get_history(user) -> List:
        user = user.current

        history = History.select(lambda h: h.user == user).sort_by(lambda h: desc(h.creation_date))
        usable = []

        for h in history:
            found = False

            if h.song:
                for u in usable:
                    if u.song == h.song:
                        found = True
            elif h.album:
                for u in usable:
                    if u.album == h.album:
                        found = True
            elif h.artist:
                for u in usable:
                    if u.artist == h.artist:
                        found = True
            elif h.search:
                for u in usable:
                    if u.search and u.search.query.lower() == h.search.query.lower():
                        found = True

            if not found:
                usable.append(h)

        return usable


class Queries(db.Entity):
    id = PrimaryKey(str)
    song = Required(Song)
    creation_date = Required(datetime, default=datetime.now)


class LyricsRequest(db.Entity):
    id = PrimaryKey(int, auto=True)
    user = Required(User)
    song = Required(Song)
    status = Required(str, default='open')
    creation_date = Required(datetime, default=datetime.now)


class LyricsSuggestion(db.Entity):
    id = PrimaryKey(int, auto=True)
    user = Required(User)
    song = Required(Song)
    status = Required(str, default='open')
    suggestion = Required(str)
    creation_date = Required(datetime, default=datetime.now)


def setup():
    db.bind(**config.DB_CON)
    db.generate_mapping(create_tables=True)
