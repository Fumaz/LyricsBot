import html
import json
import re
from functools import lru_cache
from urllib.parse import quote

import requests
from bleach import clean
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from bot import config
from genius.errors import *


class GeniusAPI:
    BASE_URL = "https://api.genius.com"
    BROWSER_AGENT = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

    def __init__(self, access_token: str):
        if not access_token:
            raise APIError('Access Token is required to use Genius API.')

        self.access_token = access_token

        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')

        self.driver = webdriver.Chrome(options=chrome_options)

    @property
    @lru_cache(maxsize=None)
    def _headers(self):
        return {
            'User-Agent': 'CompuServe Classic/1.22',
            'Accept': 'application/json',
            'Host': 'api.genius.com',
            'Authorization': f'Bearer {self.access_token}'
        }

    def _request(self, path, **kwargs):
        r = requests.get(url=f'{self.BASE_URL}{path}', headers=self._headers, params=kwargs)
        result = json.loads(r.text)

        if 'error' in result:
            raise APIError(result['error'] + ': ' + '')

        if result['meta']['status'] != 200:
            raise APIError(str(result['meta']['status']) + ': ' + result['meta']['message'])

        return result['response']

    def _selenium(self, url):
        self.driver.get(url)
        return self.driver

    @lru_cache(maxsize=None)
    def ovhlyrics(self, artist: str, title: str) -> str:
        try:
            response = json.loads(
                requests.get(url=f'https://api.lyrics.ovh/v1/{quote(artist, safe="")}/{quote(title, safe="")}').text)

            lyrics = response['lyrics'] if 'lyrics' in response else None

            if not lyrics and '&' in artist:
                artist = artist.split('&')

                for a in artist:
                    lyric = self.ovhlyrics(a.strip(), title)

                    if lyric:
                        return lyric

                return None

            return lyrics
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def strip_html(src, allowed):
        return clean(src, tags=allowed, strip=True, strip_comments=True)

    @lru_cache(maxsize=None)
    def genius_from_text(self, text) -> str:
        for line in text.split('\n'):
            if 'document.write(JSON.parse(\'\\' in line:
                to_edit: str = line
                to_edit = to_edit.split('<div class=\\\\\\"rg_embed_footer\\\\\\">')[0]
                to_edit = to_edit.replace('document.write(JSON.parse(', '').strip()
                to_edit = self.strip_html(to_edit, ['br'])
                search = ['\'\\"\\ \\\\ \\ \\ Powered by Genius\\\\\\ \\ ', '\\n', '\\']
                replace = ['', '', '']

                for i in range(len(search)):
                    to_edit = to_edit.replace(search[i], replace[i])

                to_edit = re.sub('/(\\r\\n|\\n|\\r)/gm', '', to_edit)

                while True:
                    try:
                        index = to_edit.index('\\')
                        to_edit = to_edit.replace('\\', '')
                    except:
                        break

                to_edit = to_edit.replace('\'" ', '')
                to_edit = to_edit.replace('\'"', '')
                to_edit = to_edit.replace('Powered by Genius', '')
                to_edit = html.unescape(to_edit)
                to_edit = self.strip_html(to_edit, ['br'])

                return html.unescape(to_edit.strip().replace('<br>', '\n'))

    @lru_cache(maxsize=None)
    def geniuslyrics(self, song_id: int) -> str:
        if not song_id:
            raise InvalidRequestError('Song ID cannot be None.')

        try:
            url = f'https://genius.com/songs/{song_id}/embed.js'
            response = self._selenium(url)

            return self.genius_from_text(response.page_source)
        except Exception as e:
            return None

    @lru_cache(maxsize=None)
    def oldlyrics(self, url: str) -> str:
        if not url:
            raise InvalidRequestError('Lyrics URL cannot be None.')

        return
        soup = BeautifulSoup(response, 'lxml')

        lyrics = soup.find('div', class_='lyrics')

        if not lyrics:
            lyrics = ""

        for elem in soup.find_all('div'):
            if elem.has_attr('class'):
                done = False
                for clazz in elem['class']:
                    if done:
                        break

                    if 'Lyrics' in clazz:
                        lyrics += elem.get_text(separator='\n')
                        done = True

                    else:
                        lyrics = lyrics.get_text(separator='\n')

        return lyrics

    @lru_cache(maxsize=None)
    def _track_list(self, url: str):
        if not url:
            raise InvalidRequestError('Album URL cannot be None.')

        response = requests.get(url).text
        soup = BeautifulSoup(response, 'lxml')

        json_data = json.loads(soup.find('meta[itemprop="page_data"]').attr('content'))
        songs = json_data['album_appearances']

        return [(song.track_number, song) for song in songs]

    @lru_cache(maxsize=None)
    def song(self, id: int, lyrics: bool = False, text_format: str = 'dom'):
        if not id:
            raise InvalidRequestError('Song ID cannot be None.')

        path = f'/songs/{id}'
        result = self._request(path, text_format=text_format)['song']

        scraped_lyrics = self._lyrics(result['url']) if lyrics else None

        return {**result, 'lyrics': scraped_lyrics}

    @lru_cache(maxsize=None)
    def search(self, query: str, limit: int = 50):
        if not query:
            raise InvalidRequestError('Search query cannot be None.')

        results = []
        i = 1

        while True:
            result = self._request('/search', q=query, per_page=20, page=i)
            i += 1

            for hit in result['hits']:
                results.append(hit['result'])

            if len(result['hits']) < 20:
                break

            if len(results) >= limit:
                break

        return results

    @lru_cache(maxsize=None)
    def album(self, id: int, track_list: bool = False, text_format: str = 'dom'):
        if not id:
            raise InvalidRequestError('Album ID cannot be None.')

        path = f'/albums/{id}'
        result = self._request(path, text_format=text_format)['album']

        scraped_tracks = self._track_list(result['url']) if track_list else None

        return {**result, 'track_list': scraped_tracks}

    @lru_cache(maxsize=None)
    def artist(self, id: int, text_format: str = 'dom'):
        if not id:
            raise InvalidRequestError('Artist ID cannot be None.')

        path = f'/artists/{id}'
        result = self._request(path, text_format=text_format)

        return result['artist']

    @lru_cache(maxsize=None)
    def songs_by_artist(self, id: int, page: int = 1, per_page: int = 20, sort_by: str = 'title'):
        if not id:
            return InvalidRequestError('Artist ID cannot be None.')

        path = f'/artists/{id}/songs'
        result = self._request(path, per_page=per_page, page=page, sort=sort_by)

        return result

    def clear_cache(self):
        self.lyrics.cache_clear()
        self._track_list.cache_clear()
        self.search.cache_clear()
        self.artist.cache_clear()
        self.song.cache_clear()
        self.album.cache_clear()
