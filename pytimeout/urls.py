from django.conf.urls import patterns, url


urlpatterns = patterns('pytimeout.views',
    url(r'^stopit\.ThreadingTimeout$', 'stopit_threading_timeout'),
    url(r'^gevent\.Timeout$', 'gevent_timeout'),
    url(r'^threading\.Timer$', 'threading_timer',),
    url(r'^threading\.Thread$', 'threading_thread'),
    url(r'^baseline$', 'baseline'),
    url(r'^$', 'index')
)