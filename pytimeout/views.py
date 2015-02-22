import json
import Queue
import thread
import threading
import time
import urllib2

from django.shortcuts import render
from django.http import HttpResponse
import django.core.cache
import django.db

import gevent
import stopit


### Timeout Configuration

TIMEOUT = 1
TIMEOUT_RETVAL = False


### Slow Functions

def http(delay=5):
    url = "https://httpbin.org/delay/{}".format(delay)
    urllib2.urlopen(url).read()
    return True

def cache():
    cache_key = "test"
    django.core.cache.cache.get()
    return True

def db():
    sql_query = "SELECT 1;"
    django.db.connection.cursor().execute(sql_query).fetchone()
    return True


SLOW = http
# SLOW = cache
# SLOW = db()


### Views

def index(request):
    return render(request, "index.html")

def measure(wraps):
    def wrapped(*args, **kwargs):
        start = time.time()
        completed = wraps(*args, **kwargs)
        body = json.dumps({
            "completed": completed,
            "time": '{}ms'.format(int((time.time() - start) * 1000)),
            "timeout": TIMEOUT,
            "name": wraps.__name__,
            "slow": SLOW.__name__
        }, indent=4)
        return HttpResponse(body, content_type="application/json")
    return wrapped

@measure
def baseline(request):
    return SLOW()

@measure
def threading_thread(request):
    result_queue = Queue.Queue()

    def run():
        msg = SLOW()
        result_queue.put_nowait(msg)

    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=TIMEOUT)

    try:
        return result_queue.get_nowait()
    except (Queue.Empty):
        return TIMEOUT_RETVAL

@measure
def threading_timer(request):
    def interrupt():
        thread.interrupt_main()

    try:
        threading.Timer(TIMEOUT, interrupt).start()
        return SLOW()
    except (Exception) as ex:
        return TIMEOUT_RETVAL

@measure
def gevent_timeout(request):
    with gevent.Timeout(TIMEOUT, False):
        return SLOW()
    return TIMEOUT_RETVAL

@measure
def stopit_threading_timeout(request):
    with stopit.ThreadingTimeout(TIMEOUT):
        return SLOW()
    return TIMEOUT_RETVAL