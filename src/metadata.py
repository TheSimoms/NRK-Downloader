import logging
import re
from typing import List
from urllib.parse import urlparse

import requests



METADATA_URL_ROOT = 'http://psapi-granitt-prod-ne.cloudapp.net'
METADATA_URL_SHOW = METADATA_URL_ROOT + '/series/{show_name}'
METADATA_URL_SEASON = METADATA_URL_SHOW + '/seasons/{season_id}/Episodes'
METADATA_URL_EPISODE = METADATA_URL_ROOT + '/programs/{episode_id}'

SHOW_PATTERN = re.compile(r'^/serie/(?P<show_name>[^/]+)')
EPISODE_PATTERN_NEW = re.compile(r'^/sesong/(?P<season_name>[^/]+)(?:/episode/(?P<episode_number>[^/]+))?')
EPISODE_PATTERN_OLD = re.compile(r'^/(?P<season_name>[^/]+)(?:/(?P<episode_id>[^/]+))?')

PLAYLIST_REGEX = re.compile(
    r'.*' +
    r'BANDWIDTH=(?P<bandwidth>\d+),.*' +
    r'RESOLUTION=(?P<width>\d+)x(?P<height>\d+),.*' +
    r'URL\="(?P<url>.*)"'
)

LOGGER = logging.getLogger(__name__)


class Quality:
    """Episode quality wrapper"""

    def __init__(self, bandwidth, width, height, url):
        self.bandwidth = int(bandwidth)
        self.resolution = (self.width, self.height) = (int(width), int(height))
        self.url = url

    def __gt__(self, other):
        return (self.bandwidth > other.bandwidth or
                self.width > other.width or
                self.height > other.height)

    def __str__(self):
        return 'BANDWIDTH=%s,RESOLUTION=%sx%s,URL=%s' % (
            self.bandwidth, self.width, self.height, self.url
        )

    def __repr__(self):
        return self.__str__()


class Episode:
    """Episode wrapper"""

    def __init__(
            self,
            episode_number: int,
            season_name: str,
            show_name: str,
            playlist_url: str,
            qualities: List[Quality]
    ):
        self.episode_number = episode_number
        self.season_name = season_name
        self.show_name = show_name

        self.playlist_url = playlist_url
        self.qualities = qualities

    @property
    def file_name(self) -> str:
        """Return episode filename"""

        return '{show_name}.S{season_name}E{episode_number}'.format(
            episode_number=str(self.episode_number).zfill(2),
            show_name=self.show_name.replace(' ', '.'),
            season_name=str(self.season_name).zfill(2),
        )

    @property
    def best_playlist_url(self) -> str:
        """Return playlist URL with best quality"""

        if not self.qualities:
            return self.playlist_url

        return self.playlist_url.replace(
            'master.m3u8', sorted(self.qualities, reverse=True)[0].url
        )

    def __str__(self) -> str:
        return '{show_name} S{season_name}E{episode_number}'.format(
            episode_number=str(self.episode_number).zfill(2),
            show_name=self.show_name,
            season_name=str(self.season_name).zfill(2),
        )

    def __repr__(self) -> str:
        return self.__str__()


def fetch_episode_metadata(url):
    """Fetch metadata for the given URL

    :param url: Show, season, or episode URL to fetch metadata for
    """

    url_info = extract_url_info(url)

    if url_info is None:
        LOGGER.error("Ugyldig URL: %s", url)

        return None

    return fetch_playlists_for_url(url_info)


def extract_url_info(url):
    """Extract show name, season and episode

    :param url: URL to extract info for
    :return: Dictionary containing episode info
    """

    path = urlparse(url).path

    show_match = SHOW_PATTERN.match(path)

    if show_match is None:
        return None

    show_name = show_match.group('show_name')

    path = path.split(show_name, maxsplit=1)[1]

    if episode_match := EPISODE_PATTERN_NEW.search(path):
        episode_info = episode_match.groupdict()
    elif episode_match := EPISODE_PATTERN_OLD.search(path):
        episode_info = episode_match.groupdict()
    else:
        return None

    return {
        **show_match.groupdict(),
        **episode_info,
    }


def fetch_playlists_for_url(url_info):
    """Fetch playlists for a given URL

    Fetch information from NRK's metadata provider.

    If the URL is for a show or a season, iterate the metadata
    and fetch all episode URLs.
    """

    if url_info.get('episode_id'):
        return [
            fetch_playlist_for_episode_id(url_info['episode_id']),
        ]
    if url_info.get('episode_number'):
        playlist = fetch_playlist_for_episode_number(url_info)

        return [playlist]
    if url_info.get('season_name'):
        return fetch_playlists_for_season_name(url_info)
    if url_info.get('show_name'):
        return fetch_playlists_for_show(url_info)

    return []

def fetch_playlists_for_show(url_info):
    """Fetch playlists for a given show URL"""

    show_metadata = json_request(METADATA_URL_SHOW.format(
        show_name=url_info['show_name']
    ))

    if show_metadata is None:
        return []

    playlists = []

    for season in show_metadata['seasons']:
        playlists.extend(
            fetch_playlists_for_season_id(url_info, season['id'])
        )

    return playlists

def fetch_playlists_for_season_name(url_info):
    """Fetch playlists for a given season URL"""

    season_id = get_season_id_from_season_name(url_info)

    if season_id is None:
        return []

    return fetch_playlists_for_season_id(url_info, season_id)

def fetch_playlists_for_season_id(url_info, season_id):
    """Fetch playlists for a given season URL"""

    season_metadata = json_request(METADATA_URL_SEASON.format(
        show_name=url_info['show_name'],
        season_id=season_id,
    ))

    if season_metadata is None:
        return []

    playlists = []

    for episode in season_metadata:
        episode_url = fetch_playlist_for_episode_id(episode['id'])

        if episode_url is not None:
            playlists.append(episode_url)

    return playlists

def fetch_playlist_for_episode_number(url_info):
    """Fetch playlists for a given episode URL"""

    season_id = get_season_id_from_season_name(url_info)

    if season_id is None:
        return None

    season_metadata = json_request(METADATA_URL_SEASON.format(
        show_name=url_info['show_name'],
        season_id=season_id,
    ))

    if season_metadata is None:
        return None

    episode_number = url_info['episode_number']

    try:
        episode = next(filter(
            lambda episode: episode['episodeNumber'] == int(episode_number),
            season_metadata,
        ))
    except StopIteration:
        LOGGER.error("Kunne ikke finne episode med nummber '%s'", episode_number)

        return None

    return fetch_playlist_for_episode_id(episode['id'])

def get_season_id_from_season_name(url_info):
    """Fetch season ID given a season name"""

    show_name = url_info['show_name']
    season_name = url_info['season_name']

    show_metadata = json_request(METADATA_URL_SHOW.format(
        show_name=show_name
    ))

    if show_metadata is None:
        return []

    try:
        season = next(filter(
            lambda season: season['name'] == season_name,
            show_metadata['seasons'],
        ))
    except StopIteration:
        LOGGER.error("Kunne ikke finne sesong med navn '%s'", season_name)

        return None

    return season['id']

def fetch_playlist_for_episode_id(episode_id):
    """Fetch playlists for a given episode URL"""

    episode_metadata = json_request(METADATA_URL_EPISODE.format(
        episode_id=episode_id
    ))

    if episode_metadata is None:
        return None

    try:
        playlist_url = episode_metadata['mediaAssetsOnDemand'][0]['hlsUrl']
    except (KeyError, IndexError):
        return None

    qualities = extract_playlist_qualities(playlist_url)

    return Episode(
        episode_metadata['episodeNumber'],
        episode_metadata['seasonNumber'],
        episode_metadata['seriesTitle'],
        playlist_url,
        qualities,
    )

def extract_playlist_qualities(playlist_url):
    """Extract playlist qualities from playlist URL

    :param playlist_url: Episode playlist URL
    :return: Object containing different qualities and corresponding playlist URLs
    """

    playlist = requests.get(playlist_url).text.split('\n')[1:-1]
    qualities = []

    for quality in ['%s,URL="%s"' % (playlist[i], playlist[i+1]) for i in range(0, len(playlist)-1, 2)]:
        match = PLAYLIST_REGEX.match(quality)

        if match is not None:
            qualities.append(
                Quality(
                    match.group('bandwidth'),
                    match.group('width'),
                    match.group('height'),
                    match.group('url')
                )
            )

    return qualities

def json_request(url):
    """Perform an HTTP request and parse the result as JSON"""

    response = requests.get(url=url)

    if not response.ok:
        return None

    try:
        return response.json()
    except UnicodeDecodeError:
        return None
