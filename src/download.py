import logging
import os

import ffmpeg

from metadata import Episode


LOGGER = logging.getLogger(__name__)

logging.getLogger('requests').setLevel(logging.WARNING)


def download_episode(episode: Episode, download_dir: str, extension: str) -> None:
    """Download episode

    :param download_dir: Path to download directory
    :param episode: Episode to download
    """

    download_path = generate_file_path(episode, download_dir, extension)

    LOGGER.info('Downloading episode: %s', episode)
    LOGGER.debug('Playlist URL: %s', episode.best_playlist_url)

    ffmpeg.input(episode.best_playlist_url).output(download_path).run()

def generate_file_path(episode: Episode, download_dir: str, extension: str) -> str:
    """Generate full file path from path name and file name

    :param download_dir: Path to download directory
    :param episode: Episode to download
    :param extensions: File extension

    :return Full file path
    """

    if not download_dir:
        return '{}.{}'.format(episode.file_name, extension)

    os.makedirs(download_dir, exist_ok=True)

    return '{}/{}.{}'.format(download_dir, episode.file_name, extension)
