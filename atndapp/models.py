#!-*- coding:utf-8 -*-
from google.appengine.ext import db
from google.appengine.api import urlfetch
import datetime
from xml.etree.ElementTree import *
from google.appengine.api import mail
import re
import logging
import settings_ext

class Keyword(db.Model):
  keyword = db.StringProperty(required=True)
  email = db.StringProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  updated_at = db.DateTimeProperty(auto_now=True)
  available = db.BooleanProperty(default=True)

  @classmethod
  def kind(cls):
    return "Keyword"

  def search(self):
    today = datetime.datetime.today()
    url = 'http://api.atnd.org/events/?keyword=%s&ym=%s' % (self.keyword, today.strftime('%Y%m'))
    bodies = []
    result = urlfetch.fetch(url)
    if result.status_code == 200:
      c = result.content
      elem = fromstring(c)
      events = elem.findall(".//event")
      for event in events:
        body = {}
        title = event.findtext(".//title")
        description = event.findtext(".//description")
        address = event.findtext(".//address")
        a = re.search(r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})', event.findtext(".//started-at"))
        started_at = a.group(1)+ ' ' + a.group(2)
        a = re.search(r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})', event.findtext(".//ended-at"))
        ended_at = a.group(1)+ ' ' + a.group(2)
        url = event.findtext(".//event-url")
        event_id = event.findtext(".//event-id")
        if today < datetime.datetime.strptime(started_at, "%Y-%m-%d %H:%M"): 
          body['title'] = title
          body['description'] = description
          body['address'] = address
          body['started_at'] = started_at
          body['ended_at'] = ended_at
          body['url'] = url
          body['event_id'] = event_id
          bodies.append(body)

    return bodies
      
  def send_mail(self, keyword, body):
    events = db.GqlQuery("SELECT * FROM Event WHERE keyword = :1", keyword)
    event_ids = []
    for s in events:
      event_ids.append(s.event_id)
    event_id = int(body['event_id'])
    if event_ids.count(event_id) == 0:  
      event = Event()
      event.keyword = keyword
      event.title = body['title']
      event.description = body['description']
      event.address = body['address']
      event.started_at = body['started_at']
      event.ended_at = body['ended_at']
      event.url = body['url']
      event.event_id = int(body['event_id'])
      event.email = keyword.email
      event.put() 

      content = u"""
        あなたのkeyword:[%(keyword)s]にマッチしたイベントがみつかりました！！
        <br/>
        <br/>
        [タイトル]
        %(title)s
        <br/>
        <br/>
        [内容]
        %(description)s
        <br/>
        <br/>
        [場所]
        %(address)s
        <br/>
        <br/>
        [開始日時]
        %(started_at)s
        <br/>
        <br/>
        [終了日時]
        %(ended_at)s
        <br/>
        <br/>
        [URL]
        %(url)s 
        """ % {'keyword':self.keyword,
          'title':body['title'],
          'description':body['description'],
          'address':body['address'],
          'started_at':body['started_at'],
          'ended_at':body['ended_at'],
          'url':body['url'],
          }
        
      mail.send_mail(sender=settings_ext.ADMIN_EMAIL,
                     to="%s" % (self.email),
                     subject="[ATND Notifier] matched your keyword",
                     body="%s" % content,
                     html="%s" % content
                    ) 
  
class Event(db.Model):
  @classmethod
  def kind(cls):
    return "Event"

  keyword = db.ReferenceProperty(Keyword)
  event_id = db.IntegerProperty()
  title = db.StringProperty()
  description = db.TextProperty()
  address = db.StringProperty()
  started_at = db.StringProperty()
  ended_at = db.StringProperty()
  url = db.StringProperty()
  gcal_event_link = db.TextProperty()
  email = db.StringProperty()
