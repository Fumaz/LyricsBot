from typing import Tuple

from genius.api import GeniusAPI
from .db.models import *

api = GeniusAPI(config.API_KEY)


def search(query: str, user: User = None, type: str = 'inline', limit: int = 50) -> Tuple:
    cached = Search.from_cache(query)

    if cached and cached.creation_time > datetime.now() - config.MAX_CACHE_TIME:
        r = cached
    else:
        data = api.search(query=query, limit=limit)

        r = Search.from_json(user=user, query=query, data=data, type=type)
        commit()

    return r, r.results.sort_by(lambda s: desc(s.artist.iq))[:]


def lyrics(song) -> str:
    l = api.ovhlyrics(song.artist.name, song.title)

    # if not l:
    #    l = api.geniuslyrics(song.genius_id)

    return l
