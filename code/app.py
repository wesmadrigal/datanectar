#!/usr/bin/env python
from flask import Flask

app = Flask(__name__)

from api import api
from views import views

# views
app.add_url_rule('/', view_func=views.Index.as_view('views.Index'))


# api
app.add_url_rule('/api/chains', view_func=api.Chains.as_view('views.Chains'))

app.add_url_rule('/api/chains/<type>', view_func=api.ChainType.as_view('views.ChainType'))

app.add_url_rule('/api/chains/<type>/<chain>', view_func=api.Chain.as_view('views.Chain'))

app.add_url_rule('/api/chains/<type>/<chain>/<task>', view_func=api.Task.as_view('views.Task'))

# api chain status endpoint
app.add_url_rule('/api/chainstatus', view_func=api.ChainStatus.as_view('views.ChainStatus'))

if __name__ == '__main__':
    app.run('0.0.0.0', 5000, debug=True)
