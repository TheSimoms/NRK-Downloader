import re
import subprocess
import logging
import os
import argparse

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

try:
    from urllib.parse import urlparse
except ImportError:
    from urllib2 import urlparse

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'wb')


NRK_URL_PREFIX = 'https://tv.nrk.no'
NRK_URL_REGEX_PREFIX = '(?:https?://)tv\.nrk\.no/'


class NRKDownloader:
    def __init__(self, args):
        self.urls = args.urls.split(',')
        self.file_extension = args.extension
        self.download_path = self.prepare_path(args.save_dir)
        self.debug = args.debug

        self.driver = webdriver.PhantomJS(service_args=['--ssl-protocol=any'])
        self.set_preferred_player()

    @staticmethod
    def prepare_path(path):
        """
        Remove all / from end of path name

        :param path: Path name to prepare
        :return: Prepared path name
        """

        while path.endswith('/'):
            path = path[:-1]

        return path

    @staticmethod
    def dashed_to_dotted(string):
        """
        Replace dash with dot in string

        :param string: String to parse
        :return Parsed string
        """

        return string.replace('-', '.').lower()

    @staticmethod
    def is_valid_url(url):
        """
        Check whether an URL is a valid NRK URL or not

        :param url: URL to check
        :return: Whether the URL is valid or not
        """

        return re.match(NRK_URL_REGEX_PREFIX, url) is not None

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

    def set_preferred_player(self):
        """
        Set preferred video player in the NRK website
        """

        self.driver.get('https://tv.nrk.no/innstillinger')

        self.driver.find_element(By.ID, 'rbhlslinkodm').click()
        self.driver.find_element(By.CLASS_NAME, 'save-settings').click()

    def get_url_soup(self, url, wait_for_player=False):
        """
        Get BeautifulSoup for URL

        :param url: URL to get soup for
        :return: Soup for URL
        """

        self.driver.get(url)

        if wait_for_player:
            wrapper = WebDriverWait(self.driver, 5).until(ec.presence_of_element_located((
                'id', 'nrk-player-wrapper'
            )))

            WebDriverWait(wrapper, 5).until(ec.presence_of_element_located((
                By.CSS_SELECTOR, 'a[href*="master.m3u8"]'
            )))

        return BeautifulSoup(self.driver.page_source, "lxml")

    def get_show_episode_list_urls(self, url, info):
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
                season_id = int(link.get('data-identifier'))

                episode_list_urls.append(
                    '%s/program/Episodes/%s/%s' % (NRK_URL_PREFIX, info['show'], season_id)
                )
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

        episode_list_urls = self.get_show_episode_list_urls(url, self.get_url_info(url))
        episode_urls = []

        for episode_list_url in episode_list_urls:
            soup = self.get_url_soup(episode_list_url)

            for episode_list in soup.find_all('ul', class_='episode-list'):
                for list_item in episode_list.find_all('li', class_='episode-item'):
                    url = self.parse_url('%s%s' % (
                        NRK_URL_PREFIX, list_item.find('a', class_='clearfix').get('href')
                    ))
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

        soup = self.get_url_soup(url['url'], True)

        play_button = soup.find(id='nrk-player-wrapper').find(class_='play-icon-action')

        if play_button:
            playlist_url = play_button.get('href')

            playlist_url = playlist_url.replace('/z/', '/i/')
            playlist_url = playlist_url.replace('manifest.f4m', 'master.m3u8')
            playlist_url = playlist_url.replace('master.m3u8', 'index_4_av.m3u8')

            playlist_url = {
                'url': playlist_url,
                'info': url['info']
            }

            return playlist_url
        else:
            logging.debug('No playlist URL found')

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

    def generate_file_path(self, path, file_name):
        if path is '':
            return file_name

        return '%s/%s' % (path, file_name)

    def download_episode(self, playlist_url):
        """
        Download episode from playlist URL

        :param playlist_url: URL to playlist
        """

        file_name = '%s.%s' % (self.generate_file_name(playlist_url['info']), self.file_extension)
        file_path = self.generate_file_path(self.download_path, file_name)

        logging.info('%s: Downloading episode to file' % file_name)
        logging.debug('Playlist URL: %s' % playlist_url['url'])

        args = [
            'ffmpeg',
            '-i',
            playlist_url['url'],
            file_path,
            '-c',
            'copy',
        ]

        if self.debug:
            pipe = subprocess.Popen(args)
        else:
            pipe = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        pipe.communicate()

    def start(self):
        """
        Start the process of downloading URLs
        """

        success = True

        for url in self.urls:
            success = success and self.download(url)

        return success

    def download(self, url):
        """
        Download episode(s) from NRK TV URL

        :param url: NRK TV URL
        :return Whether all episodes were downloaded successfully or not
        """

        logging.info('URL: %s' % url)

        success = True
        url = self.parse_url(url)

        if not self.is_valid_url(url):
            logging.error('%s: Invalid URL. Skipping' % url)

            return False

        try:
            logging.info('Fetching episode information for episode %s' % url)

            url_info = self.get_url_info(url)
            episode_urls = self.get_episode_urls(url, url_info)

            for episode_url in episode_urls:
                try:
                    episode_playlist_url = self.get_episode_playlist_url(episode_url)

                    if episode_url is not None:
                        self.download_episode(episode_playlist_url)
                except KeyboardInterrupt:
                    logging.info('Stopping download')

                    return False
                except Exception as e:
                    logging.error(
                        '%s: Could not download episode\nReason: %s' % (episode_url['url'], e)
                    )

                    success = False

            logging.info('Download complete')
        except Exception as e:
            logging.error('%s: An unknown error occurred. Skipping' % url)
            logging.error('Reason: %s' % e)

            return False

        return True and success


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    file_extensions = ('mkv', 'avi', )

    parser.add_argument(
        '-u', '--urls', help='Comma separated list of NRK URLs', type=str, required=True
    )
    parser.add_argument(
        '-e', '--extension', help='File extension for downloaded files',
        choices=file_extensions, default=file_extensions[0]
    )
    parser.add_argument(
        '-s', '--save_dir', help='Path to save downloaded files in. Defaults to current path',
        default=''
    )
    parser.add_argument('--debug', help='Show debug output', action='store_true')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    NRKDownloader(args).start()
