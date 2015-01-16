#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import json
from urllib import quote_plus as quote, urlencode
from urllib2 import urlopen, Request, HTTPError, URLError

API_URL = 'api.trakt.tv'
USER_AGENT = 'XBMC Add-on Trakt.tv List Manager'
NONE = 'NONE'

LIST_PRIVACY_IDS = (
    'private',
    'friends',
    'public'
)


class AuthenticationError(Exception):
    pass


class ConnectionError(Exception):
    pass


class TraktListApi():

    def __init__(self, *args, **kwargs):
        self._reset_connection()
        if args or kwargs:
            self.connect(*args, **kwargs)

    def _reset_connection(self):
        self.connected = False
        self._username = None
        self._password = None
        self._token = None
        self._api_key = None
        self._use_https = True

    def connect(self, username=None, password=None, api_key=None,
                use_https=True):
        self._username = username
        self._password = password
        self._api_key = api_key
        self._use_https = use_https
        self.connected = self.login()
        if not self.connected:
            self._reset_connection()
        return self.connected

    def get_watchlist(self):
        path = '/users/me/watchlist/movies?extended=full,images'
        return self._api_call(path, auth=True)

    def get_lists(self):
        path = '/users/me/lists'
        return self._api_call(path, auth=True)

    def search_movie(self, query):
        path = 'search/movies.json/{api_key}/?' + urlencode({'query': query})
        return self._api_call(path)

    def get_list(self, list_slug):
        path = '/users/me/lists/%s/items?extended=full,images' % (list_slug)
        return self._api_call(path, auth=True)

    def add_list(self, name, privacy_id=None, description=None):
        path = 'lists/add/{api_key}'
        post = {
            'name': name,
            'description': description or '',
            'privacy': privacy_id or LIST_PRIVACY_IDS[0]
        }
        return self._api_call(path, post=post, auth=True)

    def del_list(self, list_slug):
        path = 'lists/delete/{api_key}'
        post = {
            'slug': list_slug
        }
        return self._api_call(path, post=post, auth=True)

    def add_movie_to_list(self, list_slug, imdb_id=None, tmdb_id=None):
        if not tmdb_id and not imdb_id:
            raise AttributeError('Need one of tmdb_id, imdb_id')
        item = {'type': 'movie'}
        if tmdb_id and tmdb_id != NONE:
            item['tmdb_id'] = tmdb_id
        if imdb_id and imdb_id != NONE:
            item['imdb_id'] = imdb_id
        path = 'lists/items/add/{api_key}'
        post = {
            'slug': list_slug,
            'items': [item],
        }
        return self._api_call(path, post=post, auth=True)

    def add_movie_to_watchlist(self, imdb_id=None, tmdb_id=None):
        if not tmdb_id and not imdb_id:
            raise AttributeError('Need one of tmdb_id, imdb_id')
        item = {'type': 'movie'}
        if tmdb_id and tmdb_id != NONE:
            item['tmdb_id'] = tmdb_id
        if imdb_id and imdb_id != NONE:
            item['imdb_id'] = imdb_id
        path = 'movie/watchlist/{api_key}'
        post = {
            'movies': [item],
        }
        return self._api_call(path, post=post, auth=True)

    def del_movie_from_list(self, list_slug, imdb_id=None, tmdb_id=None):
        if not tmdb_id and not imdb_id:
            raise AttributeError('Need one of tmdb_id, imdb_id')
        item = {'type': 'movie'}
        if tmdb_id and tmdb_id != NONE:
            item['tmdb_id'] = tmdb_id
        if imdb_id and imdb_id != NONE:
            item['imdb_id'] = imdb_id
        path = 'lists/items/delete/{api_key}'
        post = {
            'slug': list_slug,
            'items': [item],
        }
        return self._api_call(path, post=post, auth=True)

    def del_movie_from_watchlist(self, imdb_id=None, tmdb_id=None):
        if not tmdb_id and not imdb_id:
            raise AttributeError('Need one of tmdb_id, imdb_id')
        item = {'type': 'movie'}
        if tmdb_id and tmdb_id != NONE:
            item['tmdb_id'] = tmdb_id
        if imdb_id and imdb_id != NONE:
            item['imdb_id'] = imdb_id
        path = 'movie/unwatchlist/{api_key}'
        post = {
            'movies': [item],
        }
        return self._api_call(path, post=post, auth=True)

    def login(self):
        path = '/auth/login'
        post = {
                'login': self._username,
                'password': self._password}
        result = self._api_call(path, post = post)
        if 'token' in result:
            self._token = result['token']
            return True
        else:
            return False 

    def _api_call(self, path, post=None, auth=False):
        if post is None: post = {}
        url = self._api_url + path
        headers = {
                   'User-Agent': USER_AGENT,
                   'Content-Type': 'application/json', 
                   'trakt-api-key': self._api_key,
                   'trakt-api-version': 2}
        
        if auth:
            if self._token is None:
                self.login()
            headers.update({
                'trakt-user-login': self._username,
                'trakt-user-token': self._token})

        self.log('_api_call using url: |%s| headers: |%s| post: |%s|' % (url, headers, post))
        if post:
            request = Request(url, json.dumps(post), headers=headers)
        else:
            request = Request(url, headers=headers)
        
        try:
            response = urlopen(request)
            json_data = json.loads(response.read())
        except HTTPError as error:
            self.log('HTTPError: %s' % error)
            if error.code == 401:
                raise AuthenticationError(error)
            else:
                raise
        except URLError as error:
            self.log('URLError: %s' % error)
            raise ConnectionError(error)
        self.log('_api_call response: %s' % repr(json_data))
        return json_data

    @property
    def _api_url(self):
        return '%s://%s' % ('https' if self._use_https else 'http', API_URL)

    def log(self, text):
        print u'[%s]: %s' % (self.__class__.__name__, repr(text))
