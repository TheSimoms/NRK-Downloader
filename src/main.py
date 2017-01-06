import argparse
import logging

from downloader import NRKDownloader


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    file_extensions = ('mkv', 'avi', )

    parser.add_argument(
        '-u', '--urls', help='Comma separated list of NRK URLs', type=str, required=True
    )
    parser.add_argument(
        '-e', '--extension', help='File extension for downloaded files',
        choices=file_extensions, default=file_extensions[0]
    )
    parser.add_argument(
        '-s', '--save_dir', help='Path to save downloaded files in.', default=''
    )
    parser.add_argument('--subtitles', help='Include subtitles', action='store_true')
    parser.add_argument('--subtitles_only', help='Download only subtitles', action='store_true')
    parser.add_argument('--debug', help='Show debug output', action='store_true')
    parser.add_argument('--silent', help='Hide browser window', action='store_true')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    NRKDownloader(args).start()
