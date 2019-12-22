# NRK-Downloader

Download episodes tv.nrk.no.

The downloader uses episode URLs for choosing what files to download. Supported URL formats:
* Show: https://tv.nrk.no/serie/side-om-side
* Season: https://tv.nrk.no/serie/side-om-side/sesong/2, https://tv.nrk.no/serie/fleksnes/1974
* Episode: https://tv.nrk.no/serie/side-om-side/sesong/2/episode/8, https://tv.nrk.no/serie/fleksnes/1974/FUHA00004874


## Requirements

* ffmpeg (apt-get install libav-tools in Ubuntu)
* Python 3
  * ffmpeg_python
  * requests


## Running

To use the downloader, run the file [main.py](src/main.py).
URLs are supplied as command line arguments.

Run ``python3 src/main.py --help`` for instructions on how to use the script.
