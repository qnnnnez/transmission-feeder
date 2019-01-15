import re
import hashlib
import base64
import unicodedata
import logging
logger = logging.getLogger('transmission-feeder')
import traceback

import feedparser
import transmission
from transmission import Transmission
import requests
import bencoder



def _calculate_infohash(torrent_data):
    torrent = bencoder.decode(torrent_data)
    return hashlib.sha1(bencoder.encode(torrent[b'info'])).hexdigest()


def _escape_filename(name):
    name = unicodedata.normalize('NFKD,', name)
    name = re.sub('[^\w\s-]', '', name).strip().lower()
    name = re.sub('[-\s]+', '', name).strip()
    name = re.sub('[/#?:;~]', '_', name)
    return name


class Feed:
    def __init__(self, name, url, filter=lambda title: True, download_dir=None, stop_after=lambda title: False):
        '''
        name: str, name of the feed, used for logging
        url: rss url
        filter: a callable, accepting a string and returning boolean, called with title of the feed entry
        download_dir: absolute path of download directory, use None if you want to use default
        stop_when: a callable, stop checking updates after it
                    Note: usually, newer items shows first
        '''
        self.name = name
        self.url = url
        self.filter = filter
        self.download_dir = download_dir
        self.stop_after = stop_after


class Feeder:
    def __init__(self, client: Transmission, session:requests.Session =None):
        self.client = client
        self.feeds = []
        self.added_infohashes = set()
        self.session = requests.Session() if session is None else session

        self.sync_infohash()

    def add_feed(self, feed: Feed):
        self.feeds.append(feed)

    def new_feed(self, *args, **kwargs):
        feed = Feed(*args, **kwargs)
        self.add_feed(feed)

    def update(self):
        for feed in self.feeds:
            self._update_feed(feed)

    def sync_infohash(self):
        self.added_infohashes.clear()
        response = self.client('torrent-get', fields=['hashString'])
        for torrent in response['torrents']:
            self.added_infohashes.add(torrent['hashString'])
        logger.info('fetched {} infohashes from transmission'.format(len(self.added_infohashes)))

    def _update_feed(self, feed):
        logger.info('updating feed "{}" from url {}'.format(feed.name, feed.url))
        fp = feedparser.parse(self.session.get(feed.url).text)
        for entry in fp['entries']:
            if not feed.filter(entry['title']):
                continue

            for link in entry['links']:
                if link['type'] != 'application/x-bittorrent' and not link['href'].endswith('.torrent'):
                    continue
                torrent_url = link['href']
                torrent = self.session.get(torrent_url).content
                infohash = _calculate_infohash(torrent)
                if infohash in self.added_infohashes:
                    logger.debug('skip already added infohash ' + infohash)
                    continue
                logger.info('adding torrent from feed "{}", title="{}"'.format(feed.name, entry['title']))
                self._add_torrent(feed, torrent, infohash)

            if feed.stop_after(entry['title']):
                logger.debug('stop checking feed "{}" because stop_after matches "{}"'.format(feed.name, entry['title']))
                break

    def _add_torrent(self, feed, torrent, infohash):
        metainfo = base64.encodebytes(torrent)
        try:
            request_args = {'metainfo': metainfo.decode('latin-1')}
            if feed.download_dir is not None:
                request_args['download_dir'] = feed.download_dir
            response = self.client('torrent-add', **request_args)
        except transmission.BadRequest:
            logger.error(traceback.format_exc())
        else:
            self.added_infohashes.add(infohash)
            logger.debug('added torrent from feed "{}", infohash={}'.format(feed.name, infohash))


def make_filter(includes=[], excludes=[], regex='.*'):
    regex = re.compile(regex)
    def filter(title):
        for include in includes:
            if include not in title:
                return False
        for exclude in excludes:
            if exclude in title:
                return False
        return not not regex.findall(title)
    return filter


def setup_logger(level):
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def main():
    pass


if __name__ == '__main__':
    main()
