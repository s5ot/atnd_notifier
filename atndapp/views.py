#!-*- coding:utf-8 -*-
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from google.appengine.ext import db
from google.appengine.api import users
from forms import KeywordForm
from models import Keyword
from models import Event
from ragendja.auth.decorators import google_login_required
import atom
import gdata.service
import gdata.auth
import gdata.alt.appengine
import gdata.calendar
import gdata.calendar.service
import settings
import re
import datetime
import logging
import settings_ext

def index(request):
  return render_to_response('atndapp/index.html', {})

@google_login_required
def top(request):
  user = users.get_current_user()

  keywords = db.GqlQuery("SELECT * FROM Keyword WHERE email = :1 AND available = :2", user.email(), True)
  current_keyword = keywords.get()

  keywords = db.GqlQuery("SELECT * FROM Keyword WHERE email = :1", user.email())
  keyword_event_cnt = {}
  for keyword in keywords:
    events = db.GqlQuery("SELECT * FROM Event WHERE keyword = :1", keyword)
    event_cnt = 0
    for e in events:
      event_cnt+=1
    keyword_event_cnt[keyword.keyword] = event_cnt

  return render_to_response('atndapp/top.html', {'user':user,
                                                  'keyword':current_keyword,
                                                  'keyword_event_cnt':keyword_event_cnt.iteritems(),
                                                  'logout_url':users.create_logout_url('/'),
                                                  })
@google_login_required
def keyword(request):
  user = users.get_current_user()

  keywords = db.GqlQuery("SELECT * FROM Keyword WHERE email = :1 AND available = :2", user.email(), True)
  current_keyword = keywords.get()

  if request.method == 'POST':
    form = KeywordForm(request.POST)
    if form.is_valid():
      if current_keyword:
        current_keyword.available = False
        db.put(current_keyword)

      keywords = db.GqlQuery("SELECT * FROM Keyword WHERE email = :1 AND keyword = :2", user.email(), form.cleaned_data['keyword'])
      keyword = keywords.get()
      
      if keyword:
        keyword.available = True
        db.put(keyword)
      else:
        new_keyword = Keyword(keyword=form.cleaned_data['keyword'], email=user.email())
        db.put(new_keyword)

      return HttpResponseRedirect('/top')
  else:
    form = KeywordForm(instance=current_keyword)

  return render_to_response('atndapp/keyword.html', {'form':form,
                                                      'user':user,
                                                      'logout_url':users.create_logout_url('/')
                                                      })

@google_login_required
def events(request):
  user = users.get_current_user()

  keywords = db.GqlQuery("SELECT * FROM Keyword WHERE email = :1 AND keyword = :2", user.email(), request.GET['keyword'])
  keyword = keywords.get()
  events = db.GqlQuery("SELECT * FROM Event WHERE keyword = :1 ORDER BY started_at DESC", keyword)

  # Create a Google Calendar client to talk to the Google Calendar service.
  calendar_client = gdata.calendar.service.CalendarService()
  # Modify the client to search for auth tokens in the datastore and use
  # urlfetch instead of httplib to make HTTP requests to Google Calendar.
  gdata.alt.appengine.run_on_appengine(calendar_client)

  token_request_url = None
  next_url = atom.url.Url('http', settings.HOST_NAME, path='/events?key=%s' % request.GET['keyword'])
  # Find an AuthSub token in the current URL if we arrived at this page from
  # an AuthSub redirect.
  auth_token = gdata.auth.extract_auth_sub_token_from_url(request.get_full_path())
  if auth_token:
    calendar_client.SetAuthSubToken(
        calendar_client.upgrade_to_session_token(auth_token))

  # Check to see if the app has permission to write to the user's
  # Google Calendar.
  if not isinstance(calendar_client.token_store.find_token(
          'http://www.google.com/calendar/feeds/'),
          gdata.auth.AuthSubToken):
      token_request_url = gdata.auth.generate_auth_sub_url(self.request.uri,
         ('http://www.google.com/calendar/feeds/default/',))

  return render_to_response('atndapp/events.html', {'events':events,
                                                    'user':user,
                                                    'token_request_url':token_request_url,
                                                    'keyword':keyword.keyword,
                                                    'logout_url':users.create_logout_url('/'),
                                                      })

@google_login_required
def stop(request):
  user = users.get_current_user()

  keywords = db.GqlQuery("SELECT * FROM Keyword WHERE email = :1 AND available = :2", user.email(), True)
  keyword = keywords.get()

  if request.method == 'POST':
      keyword.available = False
      db.put(keyword)
      return HttpResponseRedirect('/top')

  return render_to_response('atndapp/stop.html', {'user':user,
                                                        'logout_url':users.create_logout_url('/')
                                                        })
@google_login_required
def google_calendar(request):
  user = users.get_current_user()

  #events = db.GqlQuery("SELECT * FROM Event WHERE email = :1 AND key = :2", user.email(), db.Key(request.GET['key']))
  #event = events.get()
  a = re.search(r'(.+)\?', request.GET['key'])
  if a:
    key = a.group(1)
  else:
    key = request.GET['key']
  event = db.get(key)

  if event:
    event_entry = gdata.calendar.CalendarEventEntry()
    event_entry.title = atom.Title(text=event.title)
    event_entry.content = atom.Content(text=event.description)
    start_time = '%s.000+09:00' % datetime.datetime.strptime(event.started_at, "%Y-%m-%d %H:%M").isoformat()
    end_time = '%s.000+09:00' % datetime.datetime.strptime(event.ended_at, "%Y-%m-%d %H:%M").isoformat()
    event_entry.when.append(gdata.calendar.When(start_time=start_time, end_time=end_time))
    event_entry.where.append(
        gdata.calendar.Where(value_string=event.address))
    try:
      calendar_client = gdata.calendar.service.CalendarService()
      gdata.alt.appengine.run_on_appengine(calendar_client)
      calendar_client.token_store.find_token('http://www.google.com/calendar/feeds/')
      cal_event = calendar_client.InsertEvent(event_entry,
                'http://www.google.com/calendar/feeds/default/private/full')
      edit_link = cal_event.GetEditLink()
      if edit_link and edit_link.href:
        # Add the edit link to the event to use for making changes.
        event.edit_link = edit_link.href
      alternate_link = cal_event.GetHtmlLink()
      if alternate_link and alternate_link.href:
        # Add a link to the event in the Google Calendar HTML web UI.
        event.gcal_event_link = alternate_link.href
      event.put()

    # If adding the event to Google Calendar failed due to a bad auth token,
    # remove the user's auth tokens from the datastore so that they can
    # request a new one.
    except gdata.service.RequestError, request_exception:
        request_error = request_exception[0]
        if request_error['status'] == 401 or request_error['status'] == 403:
            gdata.alt.appengine.save_auth_tokens({})
        # If the request failure was not due to a bad auth token, reraise the
        # exception for handling elsewhere.
        else:
            raise
  else:
    print('I\'m sorry, you don\'t have permission to add'
                              ' this event to Google Calendar.')

  return HttpResponseRedirect('/top')


  # Check to see if the app has permission to write to the user's
  # Google Calendar.
  if not isinstance(calendar_client.token_store.find_token(
        'http://www.google.com/calendar/feeds/'),
        gdata.auth.AuthSubToken):
    token_request_url = gdata.auth.generate_auth_sub_url(next_url,
       ('http://www.google.com/calendar/feeds/default/',))

#cron action                                                       
def search(request):
  keywords = db.GqlQuery("SELECT * FROM Keyword WHERE available = :1", True)
  for keyword in keywords:
    bodies = keyword.search()
    for body in bodies:
      keyword.send_mail(keyword, body)

    return render_to_response('atndapp/search.html',{'bodies':bodies})
