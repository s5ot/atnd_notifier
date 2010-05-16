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
    year = int(today.strftime('%Y'))
    month = int(today.strftime('%m'))
    cnt = 0
    yms = []
    while cnt < 3:
      if month == 1 or 2 or 3 or 4 or 5 or 6 or 7 or 8 or 9 or 10 or 11:
        month+=1
      elif month == 12:
        year+=1
        month = 1
      yms.append("%s%02d" % (year, month))
      cnt+=1
     
    url = 'http://api.atnd.org/events/?keyword=%s&ym=%s' % (self.keyword, ",".join(yms))
    events = []
    result = urlfetch.fetch(url)
    if result.status_code == 200:
      c = result.content
      elem = fromstring(c)
      events_res = elem.findall(".//event")
      for e in events_res:
        title = e.findtext(".//title")
        description = e.findtext(".//description")
        address = e.findtext(".//address")
        a = re.search(r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})', e.findtext(".//started-at"))
        started_at = a.group(1)+ ' ' + a.group(2)
        a = re.search(r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})', e.findtext(".//ended-at"))
        ended_at = a.group(1)+ ' ' + a.group(2)
        url = e.findtext(".//event-url")
        event_id = int(e.findtext(".//event-id"))
        limit = int(e.findtext(".//limit"))
        accepted = int(e.findtext(".//accepted"))
        if today < datetime.datetime.strptime(started_at, "%Y-%m-%d %H:%M"): 
          event = Event()
          event.title = title
          event.description = description
          event.address = address
          event.started_at = started_at
          event.ended_at = ended_at
          event.url = url
          event.event_id = event_id
          event.email = self.email
          event.limit = limit
          event.accepted = accepted
          events.append(event)

    return events
      
  def send_mail(self, keyword, event):
    events = db.GqlQuery("SELECT * FROM Event WHERE keyword = :1", keyword)
    event_ids = []
    for e in events:
      event_ids.append(e.event_id)
    if event_ids.count(event.event_id) == 0:  
      event.keyword = keyword
      event.put() 

      content = u"""
        あなたのkeyword:%(keyword)sにマッチしたイベントがみつかりました！！
        <br/>
        <br/>
        [タイトル]
        <br/>
        %(title)s
        <br/>
        <br/>
        [内容]
        <br/>
        %(description)s
        <br/>
        <br/>
        [場所]
        <br/>
        %(address)s
        <br/>
        <br/>
        [開始日時]
        <br/>
        %(started_at)s
        <br/>
        <br/>
        [終了日時]
        <br/>
        %(ended_at)s
        <br/>
        <br/>
        [URL]
        <br/>
        %(url)s 
        <br/>
        <br/>
        [参加者]
        <br/>
        %(accepted)s 
        <br/>
        <br/>
        [定員]
        <br/>
        %(limit)s 
        <br/>
        <br/>
        <br/>
        <br/>
        <br/>
        <br/>
        ----
        本メールは「ATND Notifier」が送信しました。 
        <br/>
        このメールの送信元アドレスは、送信専用です。 
        <br/>
        http://atndnotifier.appspot.com 
        """ % {'keyword':self.keyword,
          'title':event.title,
          'description':event.description,
          'address':event.address,
          'started_at':event.started_at,
          'ended_at':event.ended_at,
          'url':event.url,
          'accepted':event.accepted,
          'limit':event.limit,
          }
        
      mail.send_mail(sender=settings_ext.ADMIN_EMAIL,
                     to="%s" % (self.email),
                     subject="[ATND Notifier]イベント発見通知",
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
  limit = db.IntegerProperty()
  accepted = db.IntegerProperty()

