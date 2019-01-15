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


def _extract_infos(torrent_data):
    torrent = bencoder.decode(torrent_data)
    info = torrent[b'info']
    name = info[b'name'].decode()
    length = info.get(b'length')
    if length is not None:    # single file
        return [FileInfo(name, length, [])]
    infos = []
    for file in info[b'files']:
        path = [p.decode() for p in file[b'path']]
        infos.append(FileInfo(path[-1], file[b'length'], path[:-1]))
    return infos


def _escape_filename(name):
    name = unicodedata.normalize('NFKD,', name)
    name = re.sub('[^\w\s-]', '', name).strip().lower()
    name = re.sub('[-\s]+', '', name).strip()
    name = re.sub('[/#?:;~]', '_', name)
    return name


class Feed:
    def __init__(self, name, url, filter=lambda title: True, download_dir=None, stop_after=lambda title: False,
                 file_filter=lambda fileinfo: True):
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
        self.file_filter = file_filter


class FileInfo:
    def __init__(self, name, length, path):
        self.name = name
        self.length = length
        self.path = path


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
        file_infos = _extract_infos(torrent)
        unwanted_files = []
        for i, info in enumerate(file_infos):
            if not feed.file_filter(info):
                unwanted_files.append(i)
        if len(file_infos) == len(unwanted_files):
            logger.warning('no file passes file_filter, not adding torrent: feed="{}", infohash={}'.format(feed.name, infohash))
            return

        metainfo = base64.encodebytes(torrent)
        try:
            request_args = {'metainfo': metainfo.decode('latin-1')}
            if feed.download_dir is not None:
                request_args['download_dir'] = feed.download_dir
            if unwanted_files:
                # for transmission, empty list means all files are unwanted
                # https://trac.transmissionbt.com/ticket/5615
                request_args['files_unwanted'] = unwanted_files
            response = self.client('torrent-add', **request_args)
        except transmission.BadRequest:
            logger.error(traceback.format_exc())
        else:
            self.added_infohashes.add(infohash)
            logger.debug('added torrent from feed "{}", infohash={}'.format(feed.name, infohash))


def make_str_filter(includes=[], excludes=[], regex='.*'):
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


def make_file_filter(name_filter=lambda name: True, length_filter=lambda size: True):
    def filter(info):
        return name_filter(info.name) and length_filter(info.length)
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
