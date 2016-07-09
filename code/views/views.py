#!/usr/bin/env python
import urllib2
from flask.views import View, request
from flask import render_template


class Index(View):
    def dispatch_request(self):
        try:
            urllib2.urlopen('http://www.google.com')
            # we need to be connected to the intewebs to pull down d3            
            return render_template('index.html')
        except urllib2.URLError:
            return "Hello from Datanectar"
