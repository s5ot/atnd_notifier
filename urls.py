from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
     (r'^$', 'atndapp.views.index'),
     (r'^top$', 'atndapp.views.top'),
     (r'^keyword$', 'atndapp.views.keyword'),
     (r'^stop$', 'atndapp.views.stop'),
     (r'^events$', 'atndapp.views.events'),
     (r'^google_calendar$', 'atndapp.views.google_calendar'),
     (r'^search$', 'atndapp.views.search'),

    # Example:
    # (r'^atndproject/', include('atndproject.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
