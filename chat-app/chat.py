#!/bin/env python
from app import create_app, socketio
from flask_htpasswd import HtPasswdAuth
import os

app = create_app(debug=True)
app.config['FLASK_SECRET'] = 'User authentification'
app.config['FLASK_AUTH_ALL']=True

if __name__ == '__main__':

    socketio.run(app)
