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

from xbmcswift2 import Plugin, xbmc, xbmcgui
from resources.lib.api import TraktListApi, AuthenticationError

API_KEY = '2ce240ab6543ebd7d84abe5268a822d5'

STRINGS = {
    # Root menu entries
    'new_list': 30000,
    'add_movie': 30001,
    # Context menu
    'addon_settings': 30100,
    'delete_list': 30101,
    'delete_movie': 30102,
    # Dialogs
    'enter_movie_title': 30110,
    'select_movie': 30111,
    'select_list': 30112,
    'delete_movie_head': 30113,
    'delete_movie_l1': 30114,
    'delete_list_head': 30115,
    'delete_list_l1': 30116,
    # Error dialogs
    'connection_error': 30120,
    'wrong_credentials': 30121,
    'want_set_now': 30122,
    # Noticications
    'no_movie_found': 30130,
    'success': 30131,
    # Help Dialog
    'help_head': 30140,
    'help_l1': 30141,
    'help_l2': 30142,
    'help_l3': 30143,
}


plugin = Plugin()


@plugin.route('/')
def show_lists():
    def context_menu(list_slug):
        return [
            (
                _('delete_list'),
                'XBMC.RunPlugin(%s)' % plugin.url_for(
                    endpoint='delete_list',
                    list_slug=list_slug,
                    refresh='true',
                )
            ),
            (
                _('addon_settings'),
                'XBMC.RunPlugin(%s)' % plugin.url_for(
                    endpoint='open_settings'
                )
            ),
        ]

    items = [{
        'label': '%s (%s)' % (trakt_list['name'], trakt_list['privacy']),
        'replace_context_menu': True,
        'context_menu': context_menu(trakt_list['slug']),
        'path': plugin.url_for(
            endpoint='show_list',
            list_slug=trakt_list['slug']
        )
    } for trakt_list in api.get_lists()]
    items.append({
        'label': _('new_list'),
        'path': plugin.url_for(
            endpoint='new_list',
            refresh='true',
        )
    })
    return plugin.finish(items)


@plugin.route('/list/<list_slug>/movies/')
def show_list(list_slug):
    def context_menu(list_slug, imdb_id, tmdb_id):
        return [
            (
                _('delete_movie'),
                'XBMC.RunPlugin(%s)' % plugin.url_for(
                    endpoint='delete_movie',
                    list_slug=list_slug,
                    imdb_id=imdb_id,
                    tmdb_id=tmdb_id,
                    refresh='true',
                )
            ),
            (
                _('addon_settings'),
                'XBMC.RunPlugin(%s)' % plugin.url_for(
                    endpoint='open_settings'
                )
            ),
        ]

    items = []
    plugin.set_content('movies')
    i = 0
    for i, list_item in enumerate(api.get_list(list_slug).get('items', [])):
        if not list_item['type'] == 'movie':
            continue
        movie = list_item['movie']
        items.append({
            'label': movie['title'],
            'thumbnail': movie['images']['poster'],
            'info': {
                'count': i,
                'code': movie.get('imdb_id', ''),
                'year': movie.get('year', 0),
                'plot': movie.get('overview', ''),
                'mpaa': movie.get('certification', ''),
                'genre': ', '.join(movie.get('genres', [])),
                'tagline': movie.get('tagline', ''),
                'playcount': list_item.get('plays', 0),
                'rating': movie.get('ratings', {}).get('percentage', 0) / 10.0,
                'votes': movie.get('ratings', {}).get('votes', 0)
            },
            'stream_info': {
                'video': {'duration': movie.get('runtime', 0) * 60}
            },
            'replace_context_menu': True,
            'context_menu': context_menu(
                list_slug,
                imdb_id=movie.get('imdb_id', ''),
                tmdb_id=movie.get('tmdb_id', '')
            ),
            'properties': {
                'fanart_image': movie['images']['fanart'],
            },
            'path': plugin.url_for(
                endpoint='show_help'
            ),
        })
    items.append({
        'label': _('add_movie'),
        'info': {'count': i + 1},
        'path': plugin.url_for(
            endpoint='add_movie_to_given_list',
            list_slug=list_slug,
            refresh=True,
        )
    })
    sort_methods = ['playlist_order', 'video_rating', 'video_year']
    return plugin.finish(items, sort_methods=sort_methods)


@plugin.route('/list/new')
def new_list():
    if 'title' in plugin.request.args:
        title = plugin.request.args['title'][0]
    else:
        title = plugin.keyboard(heading=_('enter_list_title'))
    if title:
        success = api.add_list(title).get('status') == 'success'
        if success:
            plugin.notify(msg=_('success'))
            refresh_on_update()


@plugin.route('/list/<list_slug>/delete')
def delete_list(list_slug):
    confirmed = xbmcgui.Dialog().yesno(
        _('delete_list_head'),
        _('delete_list_l1')
    )
    if confirmed:
        success = api.del_list(list_slug).get('status') == 'success'
        if success:
            plugin.notify(msg=_('success'))
            refresh_on_update()


@plugin.route('/list/movie/add')
def add_movie_to_list():
    movie = ask_movie()
    if movie:
        default_list_slug = plugin.get_setting('default_list_slug')
        if default_list_slug:
            list_slug = default_list_slug
        else:
            trakt_list = ask_trakt_list()
            if not trakt_list:
                return
            list_slug = trakt_list['slug']
        if list_slug:
            return plugin.redirect(plugin.url_for(
                endpoint=add_given_movie_to_given_list,
                list_slug=list_slug,
                imdb_id=movie['imdb_id'],
                tmdb_id=movie['tmdb_id']
            ))


@plugin.route('/list/<list_slug>/movie/add')
def add_movie_to_given_list(list_slug):
    movie = ask_movie()
    if movie:
        return plugin.redirect(plugin.url_for(
            endpoint=add_given_movie_to_given_list,
            list_slug=list_slug,
            imdb_id=movie['imdb_id'],
            tmdb_id=movie['tmdb_id'],
            refresh='true',
        ))


@plugin.route('/list/<list_slug>/movie/add/<imdb_id>/<tmdb_id>')
def add_given_movie_to_given_list(list_slug, imdb_id, tmdb_id):
    success = api.add_movie(
        list_slug=list_slug,
        imdb_id=imdb_id,
        tmdb_id=tmdb_id
    )
    if success:
        plugin.notify(msg=_('success'))
        refresh_on_update()


@plugin.route('/list/<list_slug>/movie/delete/<imdb_id>/<tmdb_id>')
def delete_movie(list_slug, imdb_id, tmdb_id):
    confirmed = xbmcgui.Dialog().yesno(
        _('delete_movie_head'),
        _('delete_movie_l1')
    )
    if confirmed:
        success = api.del_movie(
            list_slug,
            imdb_id=imdb_id,
            tmdb_id=tmdb_id
        ).get('status') == 'success'
        if success:
            plugin.notify(msg=_('success'))
            refresh_on_update()


def ask_movie():
    if 'title' in plugin.request.args:
        search_title = plugin.request.args['title'][0]
    else:
        search_title = plugin.keyboard(heading=_('enter_movie_title'))
    if not search_title:
        return
    movies = api.search_movie(search_title)
    if not movies:
        plugin.notify(msg=_('no_movie_found'))
        return
    items = [
        '%s (%s)' % (movie['title'], movie['year'])
        for movie in movies
    ]
    selected = xbmcgui.Dialog().select(
        _('select_movie'), items
    )
    if selected >= 0:
        selected_movie = movies[selected]
        return selected_movie


def ask_trakt_list():
    trakt_lists = api.get_lists()
    items = [trakt_list['name'] for trakt_list in trakt_lists]
    selected = xbmcgui.Dialog().select(
        _('select_list'), items
    )
    if selected >= 0:
        return trakt_lists[selected]


def refresh_on_update():
    if 'refresh' in plugin.request.args:
        xbmc.executebuiltin('Container.Refresh')


@plugin.route('/help')
def show_help():
    xbmcgui.Dialog().ok(
        _('help_head'),
        _('help_l1'),
        _('help_l2'),
        _('help_l3'),
    )


@plugin.route('/settings/default_list')
def set_default_list():
    default_list = ask_trakt_list()
    if default_list:
        plugin.set_setting('default_list', default_list['name'])
        plugin.set_setting('default_list_slug', default_list['slug'])
    else:
        plugin.set_setting('default_list', '')
        plugin.set_setting('default_list_slug', '')


@plugin.route('/settings')
def open_settings():
    plugin.open_settings()


def get_api():
    logged_in = False
    while not logged_in:
        api = TraktListApi()
        try:
            logged_in = api.connect(
                username=plugin.get_setting('username', unicode),
                password=plugin.get_setting('password', unicode),
                api_key=API_KEY,
            )
        except AuthenticationError:
            logged_in = False
        if not logged_in:
            try_again = xbmcgui.Dialog().yesno(
                _('connection_error'),
                _('wrong_credentials'),
                _('want_set_now')
            )
            if not try_again:
                return
            plugin.open_settings()
            continue
    return api


def log(text):
    plugin.log.info(text)


def _(string_id):
    if string_id in STRINGS:
        return plugin.get_string(STRINGS[string_id])
    else:
        log('String is missing: %s' % string_id)
        return string_id

if __name__ == '__main__':
    api = get_api()
    if api:
        plugin.run()
