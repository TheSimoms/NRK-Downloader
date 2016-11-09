# NRK-Downloader
Download episodes or whole shows from tv.nrk.no.

The downloader uses episode URLs (for example https://tv.nrk.no/serie/side-om-side/MUHH50000113/sesong-1/episode-1) and show URLs (for example https://tv.nrk.no/serie/side-om-side) for choosing what files to download.

## Requirements
* ffmpeg (apt-get install libav-tools in Ubuntu)
* PhantomJS
* Python 3
  * BeautifulSoup
  * Requests
  * Selenium

## Running
The downloader can be run using the command line.

To use the downloader, run the file [main.py](src/main.py).
URLs are supplied as command line arguments.

Run ``python3 src/main.py -h`` for instructions on how to use the script.
