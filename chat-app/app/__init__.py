import json
import pkg_resources
import logging
import os
import schedule

from flask import Flask
from flask_socketio import SocketIO
import socketio as sio
from flask_login import LoginManager, UserMixin
import app.users as users
import app.dialogues as dialogues
import app.config as config
import json
import random
import time


def read_models():
    models = {}
    # count previously used models
    if os.path.exists(config.past_models):
        with open(config.past_models, "r") as fp:
            models = json.load(fp)
    for model in config.tmodels:
        if model not in models:
            models[model] = 0
    return models


socketio = SocketIO(async_mode="gevent")
#socketio = sio.AsyncServer(async_handlers=True)
#socketio = sio.Server(async_mode='gevent')
all_users = users.Users()
room_numbers = [1]
active_dialogues = dialogues.Dialogues()
tmodels = read_models()

# logging
level = logging.INFO
logging.basicConfig(level=level, format='%(levelname)s: %(message)s')

# regularly cleanup online users that do not ping
def cleanup_users():
    idnums_removed, dialogues_to_remove = all_users.cleanup()
    # remove the users here!
    
    for idnum in idnums_removed:
        all_users.remove_user(idnum)
    for dialogue_id in dialogues_to_remove:
        dialogue = active_dialogues.dialogues[dialogue_id]
        # if the two users have been deconnected
        if dialogue.user1.idnum not in all_users.online_users and \
            dialogue.user2.idnum not in all_users.online_users:
            # remove room and dialogue
            room_numbers.remove(dialogue.room)
            active_dialogues.close_dialogue(dialogue_id)
            
    logging.info("Number of users online = " + str(len(all_users.online_users)))

# run a scheduler to disconnect users who haven't pinged recently
schedule.every(2).minutes.do(cleanup_users)
schedule.run_continuously()



def create_app(debug=False):
    """Create an application."""
    app = Flask(__name__)
    app.debug = debug
    app.config['SECRET_KEY'] = 'gjr39dkjn344_!67#'

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    socketio.init_app(app)
    return app

