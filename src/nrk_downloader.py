import re
import subprocess
import logging
import os
import argparse
import requests

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
NRK_URL_REGEX_PREFIX = re.compile('(?:https?://)tv\.nrk\.no/')

PLAYLIST_REGEX = re.compile(
    '.*' +
    'BANDWIDTH=(?P<bandwidth>\d+),.*' +
    'RESOLUTION=(?P<width>\d+)x(?P<height>\d+),.*' +
    'URL\="(?P<url>.*)"'
)


class Quality:
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


class NRKDownloader:
    def __init__(self, args):
        self.urls = args.urls.split(',')
        self.file_extension = args.extension
        self.download_path = self.prepare_path(args.save_dir)
        self.include_subtitles = args.subtitles
        self.only_subtitles = args.novid
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

        return NRK_URL_REGEX_PREFIX.match(url) is not None

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

    def extract_playlist_qualities(self, url):
        """
        Extract playlist qualities from playlist URL

        :param url: Episode playlist URL
        :return: Object containing different qualities and corresponding playlist URLs
        """

        try:
            playlist = requests.get(url).text.split('\n')[1:-1]
            qualities = []

            for quality in [
                '%s,URL="%s"' % (playlist[i], playlist[i+1]) for i in range(0, len(playlist)-1, 2)
            ]:
                match = PLAYLIST_REGEX.match(quality)

                if match is not None:
                    qualities.append(Quality(
                        match.group('bandwidth'),
                        match.group('width'),
                        match.group('height'),
                        match.group('url'))
                    )

            return qualities
        except Exception as e:
            return None

    def get_best_episode_playlist(self, url):
        """
        Select the best available video quality from set of available qualities

        :param qualities: Object containing the available qualities
        :return: Playlist URL for the best available quality
        """

        return url.replace(
            'master.m3u8', sorted(self.extract_playlist_qualities(url), reverse=True)[0].url
        )

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

            return self.get_best_episode_playlist(playlist_url)
        else:
            logging.debug('No playlist URL found')

    def get_subtitle_playlist_url(self, url):
        """
        Fetch subtitle playlist URL for episode

        :param url: Episode URL
        :return: Subtitle playlist URL
        """

        episode_id = url['info']['episode_id']

        return 'https://undertekst.nrk.no/prod/%s/%s/%sAA/TMP/master.m3u8' % (
            episode_id[:6], episode_id[6:8], episode_id
        )

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
        """
        Generate full file path from path name and file name

        :param path: Dir path
        :param file_name: File name
        :return Full file path
        """

        if path is '':
            return file_name

        return '%s/%s' % (path, file_name)

    def run_system_command(self, args):
        """
        Run system command using the supplied arguments
        """

        if self.debug:
            pipe = subprocess.Popen(args)
        else:
            pipe = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        pipe.communicate()

    def download_episode(self, info, episode_url=None, subtitle_url=None):
        """
        Download episode from playlist URL

        :param info: Episode info
        :param episode_url: URL to episode
        :param subtitle_url: URL to subtitles
        """

        file_name = self.generate_file_name(info)
        file_path = self.generate_file_path(self.download_path, file_name)

        episode_path = '%s.%s' % (file_path, self.file_extension)
        subtitle_path = '%s.vtt' % file_path

        logging.info('%s: Downloading episode: ' % file_name)
        logging.debug('Playlist URL: %s' % episode_url)
        logging.debug('Subtitle URL: %s' % episode_url)

        if episode_url is not None:
            self.run_system_command([
                'ffmpeg',
                '-i',
                episode_url,
                episode_path,
                '-c',
                'copy',
            ])

        if subtitle_url is not None:
            self.run_system_command([
                'ffmpeg',
                '-i',
                subtitle_url,
                subtitle_path,
                '-c',
                'copy',
            ])

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
                    args = {}

                    if not self.only_subtitles:
                        args['episode_url'] = self.get_episode_playlist_url(episode_url)

                    if self.include_subtitles or self.only_subtitles:
                        args['subtitle_url'] = self.get_subtitle_playlist_url(episode_url)

                    if episode_url is not None:
                        self.download_episode(episode_url['info'], **args)
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
    parser.add_argument('--subtitles', help='Include subtitles', action='store_true')
    parser.add_argument('--novid', help='Download only subtitles', action='store_true')
    parser.add_argument('--debug', help='Show debug output', action='store_true')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    NRKDownloader(args).start()
