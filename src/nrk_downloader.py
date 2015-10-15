import re
import urllib2
import subprocess
import sys

from bs4 import BeautifulSoup
from urlparse import urlparse


NRK_URL_PREFIX = 'https://tv.nrk.no'
NRK_URL_REGEX_PREFIX = '(?:https?://)tv\.nrk\.no/'

FILE_EXTENSION = 'mkv'


def is_valid_url(url):
    """
    Check whether an URL is a valid NRK URL or not

    :param url: URL to check
    :return: Whether the URL is valid or not
    """

    return re.match(NRK_URL_PREFIX, url) is not None


def parse_url(url):
    """
    Parse URL. Make sure it fits the script's URL format

    :param url: URL to parse
    :return: Parsed URL
    """

    return url if url[-1] == '/' else '%s/' % url


def get_url_info(url):
    """
    Extract episode info (category, show name etc.)

    :param url: URL to extract info for
    :return: Dictionary containing episode info
    """

    info = {}
    paths = urlparse(url).path[1:].split('/')[:-1]

    for path in paths:
        if 'category' not in info:
            info['category'] = path
        elif 'show' not in info:
            info['show'] = path
        elif 'episode_id' not in info:
            info['episode_id'] = path
        elif 'season' not in info:
            info['season'] = path
        elif 'episode' not in info:
            info['episode'] = path

    if 'episode' not in info and 'episode_id' in info:
        info['episode'] = info['season']

        del info['season']

    return info


def get_url_soup(url):
    """
    Get BeautifulSoup for URL

    :param url: URL to get soup for
    :return: Soup for URL
    """

    page = urllib2.urlopen(url).read()

    soup = BeautifulSoup(page)
    soup.prettify()

    return soup


def get_show_episode_list_urls(url):
    """
    Get URLs for episode list for each season in show

    :param url: Show URL
    :return: List of episode list URLs
    """

    print('Fetching episode list URLs')

    soup = get_url_soup(url)
    episode_list_urls = []

    for link in soup.find_all('a', class_='ga season-link'):
        try:
            int(link.get('data-identifier'))

            episode_list_urls.append('%s%s' % (NRK_URL_PREFIX, link.get('href')))
        except ValueError:
            pass

    return episode_list_urls


def get_show_episode_urls(url):
    """
    Get list of episode URLs for show

    :param url: Show URL
    :return: List of episode URLs
    """

    print('URL is for a show. Fetching URLs for all episodes')

    episode_list_urls = get_show_episode_list_urls(url)
    episode_urls = []

    for episode_list_url in episode_list_urls:
        soup = get_url_soup(episode_list_url)

        for episode_list in soup.find_all('ul', class_='episode-list'):
            for list_item in episode_list.find_all('li', class_='episode-item'):
                url = parse_url('%s%s' % (NRK_URL_PREFIX, list_item.find('a', class_='clearfix').get('href')))
                info = get_url_info(url)

                episode_urls.append({
                    'url': url,
                    'info': info
                })

    return episode_urls


def get_episode_urls(url, url_info):
    """
    Convert general NRK URL to list of episode URLs

    :param url: URL specified by the user. Might be show, season or episode URL
    :return: List of episode URLs
    """

    print('Fetching episode URL')

    if 'episode_id' in url_info:
        return [{
            'url': url,
            'info': url_info
        }]

    return get_show_episode_urls(url)


def get_episode_playlist_url(url):
    """
    Fetch episode playlist URL for episode

    :param url: Episode URL
    :return: Episode playlist URL
    """

    print('Fetching playlist URL for %s' % url['url'])

    soup = get_url_soup(url['url'])

    player_element = soup.find(id='playerelement')

    if player_element.get('data-media'):
        playlist_url = player_element.get('data-media')

        playlist_url = playlist_url.replace('/z/', '/i/')
        playlist_url = playlist_url.replace('manifest.f4m', 'master.m3u8')
        playlist_url = playlist_url.replace('master.m3u8', 'index_4_av.m3u8')

        playlist_url = {
            'url': playlist_url,
            'info': url['info']
        }

        return playlist_url


def dashed_to_dotted(string):
    return string.replace('-', '.').lower()


def get_file_name(info):
    file_name = dashed_to_dotted(info['show'])

    if 'season' in info:
        file_name += '.%s' % dashed_to_dotted(info['season'])

    file_name += '.%s' % dashed_to_dotted(info['episode'])

    return file_name


def download_episode(playlist_url):
    """
    Download episode from playlist URL

    :param playlist_url: URL to playlist
    :return: Path to downloaded episode
    """

    file_name = '%s.%s' % (get_file_name(playlist_url['info']), FILE_EXTENSION)

    print('Downloading episode to file %s' % file_name)

    subprocess.call([
        'avconv',
        '-i',
        playlist_url['url'],
        '-c',
        'copy',
        file_name
    ], stdout=subprocess.PIPE)


def main(url):
    print 'URL: %s' % url

    url = parse_url(url)
    url_info = get_url_info(url)

    episode_urls = get_episode_urls(url, url_info)

    for episode_url in episode_urls:
        try:
            episode_playlist_url = get_episode_playlist_url(episode_url)
            download_episode(episode_playlist_url)
        except KeyboardInterrupt:
            print('Stopping download')

            break
        except Exception as e:
            print('Could not download episode %s\nReason: %s' % (episode_url['url'], e))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('You need to supply a link for the episode or show to download')
        
        sys.exit(1)

    main(sys.argv[1])
