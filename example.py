from transmissionfeeder import *

logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

feeder = Feeder(client=Transmission(host='localhost', port=9091, username='transmission', password='transmission'))
feeder.add_feed(Feed(name='Test Feed',
                     url='https://bangumi.moe/rss/tags/5c2b732196ff38314480b616',
                     filter=make_filter(includes=['1080P', 'GB'])))

import time
while True:
    feeder.update()
    logger.debug('sleep for 3600s before next update')
    time.sleep(3600)