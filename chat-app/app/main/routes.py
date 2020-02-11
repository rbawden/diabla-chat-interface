from flask import session, redirect, url_for, render_template, request, Response, flash, send_from_directory
from . import main
import logging
from .forms import LoginForm, NewAccountForm, EvaluationForm
import os, json
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from .. import all_users, active_dialogues
import app.config as config
import time
import hashlib



# First page = instruction page
@main.route('/', methods=['POST', 'GET'])
def index():
    return render_template('instructions.html')


def read_max_nb():
    try:
        num = int(open("/home/bawden/nb_max").read().strip())
        logging.info("MAX NUMBER = " + str(num))
        return num
    except Exception:
        return 15

# Main page. Allows logging in, registering. If login is successful, goes to hub
@main.route('/login', methods=['POST', 'GET'])
def login():
    """Login form to enter a room."""
    failed_attempt = "False"
    form = LoginForm()

    language = "english"

    if request.method == "POST":
        if form.validate_on_submit():
            logging.info("I have validated the form")
            if True:
                if all_users.number_users(form.language.data) >= read_max_nb():
                    # do not allow more users to connect
                    if form.language.data == "english":
                        flash('The maximum number of users online at the same time has been reached. Please try again in a couple of minutes.')
                    else:
                        flash("Le nombre maximum d'utilisateurs simultanés à été atteint. Merci de réessayer dans quelques minutes.")
                else:

                    # store all information from login for use in the session
                    session['name'] = form.name.data
                    session['language'] = form.language.data
                    session['room'] = 1 # hub by default !important

                    # add user to user list and get unique idnum
                    session['idnum'] = all_users.add_user(form.email.data.strip().lower(),
                                                        form.language.data,
                                                        form.name.data.strip())

                return redirect(url_for('.hub'))

            #except Exception or AttributeError:
            #    logging.info("There has been ane error")
            #    return render_template('error.html')
        else:

            failed_attempt = "True"
            language = form.language.data # make the page the language chosen
            logging.info("failed attempt at validation")

    return render_template('index.html', form=form, language=language,
                            failed_attempt=failed_attempt)


# Register a new user
@main.route('/register', methods=['GET', 'POST'])
def register():
    '''Form to create a new account'''
    form = NewAccountForm()

    try:
        if form.validate_on_submit():

            # dump user to file in app/users/DATETIME.EMAIL.json
            now = datetime.now().isoformat()#strftime("%Y-%m-%d--%H-%M-%S", gmtime())
            form.time = now

            to_save = dict(form.data)
            # add some fields for later
            to_save["past_dialogues"] = []
            to_save["past_scenarios"] = []
            to_save["past_models"] = {}
            to_save['creation_date'] = now

            idnum = hashlib.sha256(form.data['email'].lower().strip().encode('utf-8')).hexdigest()
            to_save['idnum'] = idnum

            del to_save['email']
            del to_save['csrf_token']

            print(form.data)
            print(to_save)

            with open(config.user_dir+'/'+ idnum + '.json', 'w') as out:
                json.dump(to_save, out, indent=2)

            # go to login page
            return redirect('/login#registered')
    except Exception or AttributeError:
        return render_template('error.html')

    return render_template('create.html', form=form)


# Enter the hub and meet other users
@main.route('/hub')
def hub():
    """User meeting place"""

    room = session.get('room', '')
    name = session.get('name', '')
    idnum = session.get('idnum', '')
    language = session.get('language', '')

    if idnum in ['', None] or idnum not in all_users.online_users:
        return redirect(url_for('.login'))

    user = all_users.get_user_from_id(idnum)

    return render_template('hub.html', room=room, name=name, idnum=idnum, language=language)


# Chat page between two users
@main.route('/chat', methods=['GET', 'POST'])
def chat():
    """Chat room. The user's name and room must be stored in
    the session."""
    idnum = session.get('idnum', '')
    if idnum in ['', None] or idnum not in all_users.online_users or \
        all_users.get_user_from_id(idnum).room == 1 or \
        all_users.get_user_from_id(idnum).dialogue_id is None:
        return redirect(url_for('.hub'))

    user = all_users.get_user_from_id(idnum)


    logging.warn("Refreshing chat: "+ str(user))

    evalform = EvaluationForm()
    print(evalform.errors)

    dialogue = active_dialogues.dialogues.get(user.dialogue_id, None)
    if dialogue is None:
        return redirect(url_for('.hub'))

    other_user = dialogue.get_them(idnum)

    finished = str(dialogue.get_eval(idnum))
    other_person_finished = str(any([dialogue.get_eval(other_user.idnum),
                                other_user is None, other_user.room == 1,
                                other_user.idnum not in all_users.online_users]))

    logging.info(user.name)
    logging.info(finished)
    logging.info(other_user)
    logging.info(dialogue.get_eval(other_user.idnum))
    logging.info(other_person_finished)

    if request.method == "POST":
        finished = "True"
        if evalform.validate_on_submit():
            timestamp = timestamp = datetime.now().isoformat()
            # send evaluation form to dialogues

            dialogue.add_final_evaluation(idnum, timestamp, evalform.data)
            logging.warn("Adding final evaluation: "+ str(user))

            # if other user has gone, delete dialogue now
            if dialogue.get_them(idnum).dialogue_id != user.dialogue_id:
                active_dialogues.close_dialogue(user.dialogue_id)

            # remove dialogue info from user
            user.dialogue_id = None
            user.room = 1

            return redirect(url_for('.hub'))

    return render_template('chat.html', name=user.name, room=user.room,
                                        form=evalform, idnum=user.idnum,
                                        language=user.language,
                                        finished=finished,
                                        other_person_finished=other_person_finished)


# Display the transcription
@main.route('/transcription')
def transcription():
    idnum = session.get('idnum', '')
    user = all_users.get_user_from_id(idnum)

    if user is None:
        return render_template('error.html')

    # Error page if not defined

    return render_template('transcription.html', name=user.name, room=user.room,
                                        idnum=user.idnum,
                                        language=user.language)


@main.route('/robots.txt')
def static_from_root():
    return send_from_directory(main.static_folder, request.path[1:])
