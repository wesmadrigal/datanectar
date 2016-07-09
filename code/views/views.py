#!/usr/bin/env python
import urllib2
from flask.views import View, request
from flask import render_template


class Index(View):
    def dispatch_request(self):
        return "Hello from Datanectar"
