# NRK-Downloader
Download episodes or whole shows from tv.nrk.no.

The downloader uses episode URLs (for example https://tv.nrk.no/serie/side-om-side/MUHH50000113/sesong-1/episode-1) and show URLs (for example https://tv.nrk.no/serie/side-om-side) for choosing what files to download.

## Requirements
* avconv (apt-get install libav-tools)
* Python 2.7
  * BeautifulSoup
  * TkInter (only for the graphical user interface)

## Running
The downloader can be run using either command line or a simple graphical user interface.

### Command line
To run the downloader using command line, run the file [nrk_downloader.py](src/nrk_downloader.py).
URLs are supplied as command line arguments.

### Graphical user interface
To run the downloader using the graphical user interface, run the file [app.py](src/app.py).
