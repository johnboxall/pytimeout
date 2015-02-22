# pyTimeout ⌚

A little experiment at limiting function execution time in the request/response
cycle of a Python web server using Django and Gunicorn.

While working on Django app, I was curious as to whether I could limit the
execution time of a particular view to ensure it would return before a deadline,
like [Heroku's request timeouts](https://devcenter.heroku.com/articles/request-timeout#timeout-behavior).

In my mind, the perfect Python code would look something like this:

```python
def view(request):
    with timeout(seconds=5):
        sometimes_really_slow()
    # ...
    return response
```

[I turned to Google](https://www.google.ca/search?q=python+timeouts).

It seems this is an area of some confusion! I looked at four ways to implement
timeouts in Python:

* [Signal timeouts using `signal.alarm()`](https://docs.python.org/2/library/signal.html#signal.alarm)
* [Thread timeouts using `threading.Thread.join()`](https://docs.python.org/2/library/threading.html#threading.Thread.join)
* [Process timeouts using `multiprocessing.Process.join()`](https://docs.python.org/2/library/multiprocessing.html#multiprocessing.Process.join)
* [Network I/O timeouts, like the one found in `urllib2.urlopen()`](https://docs.python.org/2/library/urllib2.html#urllib2.urlopen)

Given my code need to work in the context of a Gunicorn server I ruled out
signals, as I probably wouldn't be the only one listening.

I hestiant to investigate subprocesses, as it wasn't clear how this would effect
the resource utliziation of my app even with Linux's copy on write process
semantics.

I made a note to use network I/O timeouts whenever available.

But it seemed like threading might give me the magic to write my dream code.

This repo walks through different threading based approaches to execution
timeouts.

## Things that could be slow!

Generally for production web app applications that have achieved traction, we're
aiming for sub-second responses. If something is consistently taking much longer
to respond its probably time to break out caching.

But occassionally even a well tuned app can have hicups. In particular, many
web apps exhibit poor performance in the face of bad network conditions.

Included in this project are three functions that may be intermittently be slow
in bad network conditions:

* `http()` makes an HTTP request to (HTTPBin's)[https://httpbin.org] [`delay`]
  endpoint which takes `n` seconds to respond.
* `cache()` fetchs a key from a Memcached server. Using the Linux traffic control
  tool, [`tc`](http://tldp.org/HOWTO/Traffic-Control-HOWTO/intro.html), We can
  simulate a wide range of poor network conditions that kill the performance of
  this seemingly harmless function.
  ```shell
  # Add 100ms delay to localhost routing. Don't use this on Prod kids.
  tc qdisc add dev lo root handle 1:0 netem delay 100msec
  # Reset it!
  tc qdisc del dev lo root
  ```
* `db()` executes a simple database query against a MySQL server. Again, with
  traffic control, we can create network conditions which play havoc with the
  execution time of this function.

## Approaches to timeout execution

I implemented a number of Django views which take different approaches to timing
out the execution of a slow function:

* `threading.Thread` pushes the execution to a worker thread. The thread continues
  runs in the background even after the timeout, but the view returns it's response.
* `threading.Timer` interrupts the main thread after the timeout by throwing a
  `KeyboardException`. Unfortunately, it isn't clear where in the code this will
  be thrown, so I abandoned this approach.
* `gevent.Timeout` uses `gevent`'s timeout mechanism to limit execution.
* `stopit.ThreadingTimeout` uses the `stopit` modules timeout mechanism.

# Recommendations

When you're running in the context of a web server linke Gunicorn, I think
enforcing a function timeout is more trouble than it's worth.

Instead, I'd try these more maintainable alternatives:

- Limit execution at the web server level using [Gunicorn's timeouts](http://docs.gunicorn.org/en/develop/configure.html#timeout)
  or [uWSGI's harakiri](http://uwsgi-docs.readthedocs.org/en/latest/Options.html#harakiri).
- Tracing long execution using logging or other application telemetry. Use what
  you learn to stop timeouts from happening in the first place.
- Offload long running tasks somewhere else! If something is consistently taking
  long enough to timeout, it is probably better run on in another process like
  a worker or cron job where you'll have more control of the execution and less
  deadlines to worry about!

If you've really must handle function execution time limits inside the
request/response cycle, then it seems like threads (or green threads) will get
you there, but I'd recommend looking further at their effect on the performance
characteristics or your application before cutting over.

## Setup and Usage

You can install pyTimeout locally and run it. It comes with a VirtualBox Vagrant
instance for more in depth testing.

```bash
git clone ... ; cd pytimeout
vagrant up
vagrant ssh

# In the VM!
cd /vagrant
virtualenv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Run a server. Vagrant forwards 8000 to localhost:8000
gunicorn pytimeout.wsgi --worker-class gevent --bind 0.0.0.0:8000
```

To test Memcached or MySQL, set them up:

```bash
sudo service memcached start
# Configure the relevant sections in `settings.py`
vi settings.py

sudo service mysql start
# Create a MySQL DB
...
# Configure the relevant sections in `settings.py`
vi settings.py

# Toggle the settings `views.py`
vi pytimeout/views.py
```

## Deployment

An instance of pyTimeout running Gunicorn using gevent workers runs on Heroku:

https://pytimeout.herokuapp.com/

[Note that its using Python 2.7.8 to avoid an existing gevent bug](https://github.com/gevent/gevent/issues/477).