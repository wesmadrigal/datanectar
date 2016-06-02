#!/usr/bin/env python
from flask.views import View, request
from flask import render_template


class Index(View):
    def dispatch_request(self):
        return render_template('index.html')
