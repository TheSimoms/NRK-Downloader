import re
import urllib2
import subprocess
import sys
import logging
import os

from bs4 import BeautifulSoup
from urlparse import urlparse

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'wb')


NRK_URL_PREFIX = 'https://tv.nrk.no'
NRK_URL_REGEX_PREFIX = '(?:https?://)tv\.nrk\.no/'


class NRKDownloader:
    def __init__(self):
        self.path = ""
        self.file_extensions = ('mkv', 'avi', )
        self.file_extension = self.file_extensions[0]
        self.urls = []

    @staticmethod
    def is_valid_url(url):
        """
        Check whether an URL is a valid NRK URL or not

        :param url: URL to check
        :return: Whether the URL is valid or not
        """

        return re.match(NRK_URL_PREFIX, url) is not None

    @staticmethod
    def parse_url(url):
        """
        Parse URL. Make sure it fits the script's URL format

        :param url: URL to parse
        :return: Parsed URL
        """

        return url if url[-1] == '/' else '%s/' % url

    @staticmethod
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

    @staticmethod
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

    def get_show_episode_list_urls(self, url):
        """
        Get URLs for episode list for each season in show

        :param url: Show URL
        :return: List of episode list URLs
        """

        logging.info('%s: Fetching episode list URLs' % url)

        soup = self.get_url_soup(url)
        episode_list_urls = []

        for link in soup.find_all('a', class_='ga season-link'):
            try:
                int(link.get('data-identifier'))

                episode_list_urls.append('%s%s' % (NRK_URL_PREFIX, link.get('href')))
            except ValueError:
                logging.error('%s: Could not find episode list' % url)

        return episode_list_urls

    def get_show_episode_urls(self, url):
        """
        Get list of episode URLs for show

        :param url: Show URL
        :return: List of episode URLs
        """

        logging.info('%s: URL is for a show. Fetching URLs for all episodes' % url)

        episode_list_urls = self.get_show_episode_list_urls(url)
        episode_urls = []

        for episode_list_url in episode_list_urls:
            soup = self.get_url_soup(episode_list_url)

            for episode_list in soup.find_all('ul', class_='episode-list'):
                for list_item in episode_list.find_all('li', class_='episode-item'):
                    url = self.parse_url('%s%s' % (NRK_URL_PREFIX, list_item.find('a', class_='clearfix').get('href')))
                    info = self.get_url_info(url)

                    episode_urls.append({
                        'url': url,
                        'info': info
                    })

        return episode_urls

    def get_episode_urls(self, url, url_info):
        """
        Convert general NRK URL to list of episode URLs

        :param url: URL specified by the user. Might be show, season or episode URL
        :return: List of episode URLs
        """

        logging.info('%s: Fetching episode URL(s)' % url)

        if 'episode_id' in url_info:
            return [{
                'url': url,
                'info': url_info
            }]

        return self.get_show_episode_urls(url)

    def get_episode_playlist_url(self, url):
        """
        Fetch episode playlist URL for episode

        :param url: Episode URL
        :return: Episode playlist URL
        """

        logging.info('%s: Fetching playlist URL' % url['url'])

        soup = self.get_url_soup(url['url'])

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

    @staticmethod
    def dashed_to_dotted(string):
        """
        Replace dash with dot in string

        :param string: String to edit
        """

        return string.replace('-', '.').lower()

    def generate_file_name(self, info):
        """
        Generate episode file name

        :param info: Dictionary with info of file to generate file name for
        :return Episode file name
        """

        file_name = self.dashed_to_dotted(info['show'])

        if 'season' in info:
            file_name += '.%s' % self.dashed_to_dotted(info['season'])

        file_name += '.%s' % self.dashed_to_dotted(info['episode'])

        return file_name

    def download_episode(self, playlist_url):
        """
        Download episode from playlist URL

        :param playlist_url: URL to playlist
        """

        file_name = '%s.%s' % (self.generate_file_name(playlist_url['info']), self.file_extension)

        logging.info('%s: Downloading episode to file' % file_name)

        subprocess.call([
            'avconv',
            '-y',
            '-i',
            playlist_url['url'],
            '-c',
            'copy',
            file_name
        ], stdout=DEVNULL, stderr=subprocess.STDOUT)

    def download_multiple(self, urls):
        for url in urls:
            self.download(url)

    def download(self, url):
        """
        Download episode(s) from NRK TV URL(s)

        :param urls: NRK TV URL(s)
        """

        logging.info('URL: %s' % url)

        url = self.parse_url(url)

        if not self.is_valid_url(url):
            logging.error('%s: Invalid URL. Skipping' % url)

            return

        try:
            url_info = self.get_url_info(url)

            episode_urls = self.get_episode_urls(url, url_info)

            for episode_url in episode_urls:
                try:
                    episode_playlist_url = self.get_episode_playlist_url(episode_url)
                    self.download_episode(episode_playlist_url)
                except KeyboardInterrupt:
                    logging.info('Stopping download')

                    break
                except Exception as e:
                    logging.error('%s: Could not download episode\nReason: %s' % (episode_url['url'], e))

            logging.info('Download complete')
        except Exception as e:
            logging.error('%s: An unknown error occurred. Skipping' % url)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error('You need to supply at least one link for an episode to download')

        sys.exit(1)

    logging.basicConfig(level=logging.INFO)

    NRKDownloader().download_multiple(sys.argv[1:])
