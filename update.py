import os
import logging
import urllib2
import traceback
import subprocess
import Queue
from threading import Thread

ROOT = os.path.abspath(os.path.dirname(__file__))
path = lambda *x: os.path.join(ROOT, *x)

DEFAULT_BASE_URL = 'http://etherpad.mozilla.com:9000/'
DEFAULT_FORMAT = 'txt'
DEFAULT_DIR = path('etherpads')

COMMIT_MSG = 'Automated update of etherpads.'
COMMIT_AUTHOR = 'System <no-reply@hackasaurus.org>'

def make_file(pad, format=DEFAULT_FORMAT, dirname=DEFAULT_DIR):
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    filename = '%s.%s' % (pad, format)
    return open(os.path.join(dirname, filename), 'w')

def make_url(pad, format=DEFAULT_FORMAT, url=DEFAULT_BASE_URL):
    if format not in ('txt', 'html'):
        raise Exception("unknown format: %s" % format)
    d = dict(url=url, pad=pad, format=format)
    return "%(url)sep/pad/export/%(pad)s/latest/?format=%(format)s" % d

def refresh_pads(pads, urlopen=urllib2.urlopen, make_file=make_file,
                 make_url=make_url):
    def worker():
        while True:
            try:
                pad = queue.get(True, 0.1)
            except Queue.Empty:
                return
            try:
                response = urlopen(make_url(pad)).read()
                make_file(pad).write(response)
                print "fetched %s" % pad
            except Exception, e:
                msg = "Error fetching %s:\n%s" % (
                  pad,
                  traceback.format_exc(e)
                  )
                logging.error(msg)
            finally:
                queue.task_done()

    NUM_WORKER_THREADS = 5

    queue = Queue.Queue()
    
    for pad in pads:
        queue.put(pad)

    for i in range(NUM_WORKER_THREADS):
        t = Thread(target=worker)
        t.start()

    queue.join()

if __name__ == '__main__':
    os.chdir(path('.'))
    subprocess.check_call(['git', 'pull'])

    f = open(path('pads.txt'), 'r')
    refresh_pads([pad.strip() for pad in f if pad.strip()])
    
    for filename in os.listdir(DEFAULT_DIR):
        fullpath = os.path.join(DEFAULT_DIR, filename)
        subprocess.check_call(['git', 'add', fullpath])
    subprocess.call(['git', 'commit', '-m', COMMIT_MSG, '--author',
                     COMMIT_AUTHOR])
    subprocess.check_call(['git', 'push'])
