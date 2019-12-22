import argparse
import logging

from metadata import fetch_episode_metadata
from download import download_episode


def run():
    """Run the downloader"""

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    file_extensions = ('mkv', 'avi', )

    parser.add_argument(
        '-u', '--urls', type=str, required=True, nargs='+'
    )
    parser.add_argument(
        '-e', '--extension', help='File extension for downloaded files',
        choices=file_extensions, default=file_extensions[0]
    )
    parser.add_argument('-s', '--save_dir', help='Path to save downloaded files in.', default='')
    parser.add_argument('--debug', help='Show debug output', action='store_true')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    for url in args.urls:
        episodes = fetch_episode_metadata(url)

        for episode in episodes:
            download_episode(episode, args.save_dir, args.extension)


if __name__ == "__main__":
    run()
