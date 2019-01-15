# transmission-feeder

Simple python library to add torrents from RSS feeds

## How To Use

Install dependencies first: `pip install -r requirements.txt`

Then you can make a copy of `example.py` and modify it however you want.
Run your script and torrents will be added.
You can add it to your crontab for automatic updates.

## How Does It Work

When `Feeder.update()` is called, every added URL are checked.

Feed XMLs will be downloaded, and for every item in the feed that passes the `Feed.filter`, if a `<link>` it contains points to a `.torrent` file, the torrent file will be downloaded.

Then the torrent file will be decoded to get some meta-information, namely name and length, about files it contains.
That's when `Feed.file_filter`s are applied.

When adding torrents, torrent files (instead of its URL) will be sent to Transmission, so Transmission will not download the torrent file from Internet.
