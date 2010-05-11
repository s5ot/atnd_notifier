from django.forms import ModelForm
from django import forms
from google.appengine.ext.db import djangoforms
import models

class KeywordForm(djangoforms.ModelForm):
  class Meta:
    model = models.Keyword
    exclude = ['email', 'created_at', 'updated_at', 'available']

