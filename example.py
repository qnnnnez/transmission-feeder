from transmissionfeeder import *

setup_logger(logging.DEBUG)

feeder = Feeder(
    client=Transmission(
        host='localhost',
        port=9091,
        username='transmission',
        password='transmission',
    ),
)

'''
# feeder.session configuration
# feeder.session is a requests.Session object, see http://docs.python-requests.org/en/master/user/advanced/#session-objects
# By modifying the object, you can control how feeder sends HTTP requests:
feeder.session.auth('user', 'pass')    # http basic auth
feeder.session.cookies.set('cookie-name', 'cookie-value')    # add a cookie
feeder.session.proxies = {'http': 'foo.bar:3128', 'http://host.name': 'foo.bar:4012'}    # proxy settings
'''

feeder.new_feed(
    name='Endro',
    url='https://bangumi.moe/rss/tags/5c2b732196ff38314480b616',
    filter=make_filter(includes=['1080P', 'GB']),
    download_dir=None,
    stop_after=make_filter(includes=['[01]']),
)

logger.info('feeder.update()')
feeder.update()
logger.info('update done')