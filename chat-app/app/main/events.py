#! coding: utf-8
from websocket import create_connection
from flask import session, request
from flask_socketio import emit, join_room, leave_room
from .. import socketio, all_users, room_numbers, active_dialogues
import os
from w3lib.html import replace_entities
from datetime import datetime
import requests
import json
import subprocess
import app.config as config
import schedule
import re
import random
import logging
import app.settings as settings
#from nltk.tokenize import sent_tokenize
import hashlib
import time

random.seed(time.time())

def timecode():
    return datetime.now().isoformat()

def PLOG(time, user, dialogue, msgtype, msg, model=""):
    os.sys.stdout.write("\t".join([msgtype, dialogue, user, msg, model, time])+"\n")
    os.sys.stdout.flush()

# User joins the hub (either from login or from a dialogue)
@socketio.on('joined', namespace='/hub')
def joined(message):
    """Sent by clients when they enter the hub.
    A status message is broadcast to all people in the room."""
    idnum = session.get('idnum')

    # skip if not connected
    if idnum is None or idnum not in all_users.online_users:
        return
    user = all_users.online_users[idnum]
    dialogue_id = user.dialogue_id

    logging.warn("User just joined hub: "+str(user))

    # if should be in dialogue, send back there!
    if dialogue_id is not None and dialogue_id in active_dialogues.dialogues:
        msg = {"english": "Please do not navigate away to another window in the middle of the dialogue. You will now be taken back to the dialogue.",
               "french": "Merci de ne pas quitter la fenêtre au milieu du dialogue. Vous serez ramené(e) vers l'écran de dialogue."}
        emit('send_back_to_dialogue', {'msg': msg[user.language]}, room=user.sid)

        return # do not go any further

    # Otherwise do this as usual (set all values to default)
    #user.dialogue_id = None
    room = 1 # ensure that the room number is 1 for the hub
    join_room(room)
    user.room = room

    if not (idnum in ['', None] or idnum not in all_users.online_users) and \
        user.room == 1:
        all_users.change_sid(idnum, request.sid)
        PLOG(timecode(), idnum, "", "JOINED HUB", "")
        emit('user_enters', {}, room=room)

    # How about checking other users now?
    users_removed, dialogues_to_remove = all_users.cleanup()

    # remove users
    for idnum in users_removed:
        emit('disconnected_timeout', {}, room=all_users.get_user_from_id(idnum).sid, namespace="/hub")
        emit('disconnected_timeout', {}, room=all_users.get_user_from_id(idnum).sid, namespace="/chat")
        all_users.remove_user(idnum)
    # remove dialogues
    for dialogue_id in dialogues_to_remove:
        dialogue = active_dialogues.dialogues[dialogue_id]
        # if the two users have been deconnected
        if dialogue.user1.idnum not in all_users.online_users and \
            dialogue.user2.idnum not in all_users.online_users:
            # remove room and dialogue
            room_numbers.remove(dialogue.room)
            active_dialogues.close_dialogue(dialogue_id)

    # refresh other users
    for idnum in all_users.hub_users:
        user_ids, user_names, user_langs, user_rooms = all_users.get_list_users_all()
        user = all_users.get_user_from_id(idnum)
        emit('show_users', {'name': session.get('name'), 'idnum': idnum,
                            'room': room, 'user_list': user_names,
                            'user_ids' : user_ids, 'user_langs': user_langs,
                            'rooms': user_rooms}, room=user.sid)


# The hub is refreshed
@socketio.on('refresh_hub', namespace='/hub')
def refresh_hub(data):
    """Sent every x seconds to refresh the user list"""
    room = session.get('room') # should be 1
    idnum = session.get('idnum')

    if not (idnum in ['', None] or idnum not in all_users.online_users):
        user = all_users.get_user_from_id(idnum)
        join_room(room)
        user_ids, user_names, user_langs, user_rooms = all_users.get_list_users_all()

        emit('show_users', {'name': session.get('name'), 'idnum': idnum,
                            'room': room, 'user_list': user_names,
                            'user_ids' : user_ids, 'user_langs': user_langs,
                            'rooms': user_rooms}, room=room)

# User leaves the hub
@socketio.on('log_out', namespace='/hub')
def log_out(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    idnum = session.get('idnum')

    # remove this user and leave the room
    all_users.remove_user(idnum)
    leave_room(room)

    # refresh other users
    for idnum in all_users.hub_users:
        user_ids, user_names, user_langs, user_rooms = all_users.get_list_users_all()
        user = all_users.get_user_from_id(idnum)
        emit('show_users', {'name': session.get('name'), 'idnum': idnum,
                            'room': room, 'user_list': user_names,
                            'user_ids' : user_ids, 'user_langs': user_langs,
                            'rooms': user_rooms}, room=user.sid)

# User leaves the hub
@socketio.on('logout', namespace='/chat')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    idnum = session.get('idnum')

    all_users.remove_user(idnum)
    leave_room(room)


# A client (active) has clicked on another client (passive) to initiate a chat
@socketio.on('chat_to_me', namespace='/hub')
def chat_to_me(data):
    '''A chat has been initiated by active user with passive user'''
    id1 = data['passive_id']
    id2 = data['active_id']
    u1 = all_users.get_user_from_id(id1)
    u2 = all_users.get_user_from_id(id2)

    if u1 is None or u2 is None:
        return

    #name1 = all_users.get_user_from_id(id1).name
    #name2 = all_users.get_user_from_id(id2).name

    txt_waiting = {"english": "Waiting for "+ u1.name+ "'s answer…",
                   "french": "En attente la réponse de "+ u1.name+"…"}
    txt_invited = {"english": "You have been invited to chat by "+ u2.name+ ".",
                   "french": u2.name+" vous a invité(e) à dialoguer."}

    emit('waiting', {'msg': txt_waiting[u2.language]}, room=u2.sid)
    emit('asked_to_chat', {'message': txt_invited,
                           'active_id': id2,
                           'passive_id': id1}, room=u1.sid)

# Receive ping from user
@socketio.on('ping-hub', namespace='/hub')
def receive_ping_hub(data):
    idnum = data['idnum']

    logging.warn("Hub ping from " + idnum)
    logging.warn(str(all_users))
    user = all_users.get_user_from_id(idnum)
    if user is None:
        return
    user.pinged(source="hub")
    all_users.change_sid(idnum, request.sid)

    dialogue_id = user.dialogue_id
    # if should be in dialogue, send back there!
    if dialogue_id is not None and dialogue_id in active_dialogues.dialogues:
        logging.info("Trying with the sid = " + user.sid)
        msg = {"english": "Please do not navigate away to another window in the middle of the dialogue. You will now be taken back to the dialogue.",
               "french": "Merci de ne pas quitter la fenêtre au milieu du dialogue. Vous serez ramené(e) vers l'écran de dialogue."}
        emit('send_back_to_dialogue', {'msg': msg[user.language]}, room=user.sid)

        return # do not go any further

# Receive ping from user
@socketio.on('ping_alert_open', namespace='/hub')
def receive_ping_alert_open_hub(data):
    idnum = data['idnum']

    logging.warn("User has an alert box open")
    user = all_users.get_user_from_id(idnum)
    if user is None:
        return
    user.alert = True

# Receive ping from user
@socketio.on('ping_alert_close', namespace='/hub')
def receive_ping_alert_close_hub(data):
    idnum = data['idnum']

    logging.warn("User has closed the alert box")
    user = all_users.get_user_from_id(idnum)
    if user is None:
        return
    user.alert = False

# Receive ping from user
@socketio.on('ping_alert_open', namespace='/chat')
def receive_ping_alert_open_chat(data):
    idnum = data['idnum']

    logging.warn("User has an alert box open")
    user = all_users.get_user_from_id(idnum)
    if user is None:
        return
    user.alert = True

# Receive ping from user
@socketio.on('ping_alert_close', namespace='/chat')
def receive_ping_alert_close_chat(data):
    idnum = data['idnum']

    logging.warn("User has closed the alert box")
    user = all_users.get_user_from_id(idnum)
    if user is None:
        return
    user.alert = False





# Receive ping from user
@socketio.on('ping-chat', namespace='/chat')
def receive_ping_chat(data):
    idnum = data['idnum']
    logging.warn("Chat ping from " + idnum)
    logging.warn(str(all_users))
    user = all_users.get_user_from_id(idnum)

    if user is None:
        return

    user.pinged(source="chat")

    # pong all Users
    for userid in all_users.online_users:
        1
        #emit("pong", {}, room=all_users.get_user_from_id(userid).sid)

    # if other user is no longer there, then close dialogue
    user = all_users.get_user_from_id(idnum)
    if data["on_connect"] == "False" and user.dialogue_id is not None:
        other_user = active_dialogues.dialogues[user.dialogue_id].get_them(idnum)


        if other_user is None or other_user.dialogue_id != user.dialogue_id or \
            other_user.idnum not in all_users.online_users:
            dialogue = active_dialogues.dialogues[user.dialogue_id]

            #logging.warning(other_user.dialogue_id != user.dialogue_id)
            #logging.warning(other_user.idnum not in all_users.online_users)
            #logging.warn(other_user.idnum in all_users.hub_users)
            #logging.warning("A user has disappeared: "+str(other_user))
            # if dialogue has not already ended
            if user.room == dialogue.room and not dialogue.get_eval(idnum):
                dialogue.set_eval(idnum)
                if user.language == "english":
                    msg = 'The dialogue has been ended. To go to the final evaluation step, click on \'finish this dialogue\'.'
                else:
                    msg = "The dialogue a été terminé. Pour passer à la dernière étape d'évaluation, cliquez sur 'finir ce dialogue'."
                emit('abandoned', {'msg': msg},
                    room=user.sid)


# Refusal to chat
@socketio.on('refuse_chat', namespace='/hub')
def refuse_chat(data):
    '''Passive user has rejected the chat'''
    id1 = data['passive_id']
    id2 = data['active_id']
    name1 = all_users.get_user_from_id(id1).name

    emit('chat_refusal', {'passive_name': name1}, room=all_users.get_user_from_id(id2).sid)


# Acceptance of a conversation with someone - initiates the dialogue
@socketio.on('accept_chat', namespace='/hub')
def accept_chat(data):
    id1 = data['passive_id']
    id2 = data['active_id']

    # ready to chat
    user1 = all_users.get_user_from_id(id1)
    user2 = all_users.get_user_from_id(id2)

    if user1 is None or user2 is None:
        return

    # check whether both users are still available!
    if user1 is None or user2 is None:
        msgs = {'english': 'The other user has logged out.',
                'french': "Votre interlocuteur/trice s'est déconnecté(e)."}
        emit('user_no_longer_there', {'msg': msgs[user1.language]}, room=user1.sid)
        emit('user_no_longer_there', {'msg': msgs[user2.language]}, room=user2.sid)
    elif user1.room != 1 or user2.room !=1:
        msgs = {'english': ' has started a dialogue elsewhere.',
                'french': "Votre interlocuteur/trice a commencé un autre dialogue et n'est plus disponible."}
        emit('user_no_longer_there', {'msg': msgs[user1.language]}, room=user1.sid)
        emit('user_no_longer_there', {'msg': msgs[user2.language]}, room=user2.sid)
        return

    user1.ready_to_chat = True
    user2.ready_to_chat = True

    timestamp = datetime.now().isoformat()
    # get user information (sort users by language)
    if user1.language > user2.language:
        u1, u2 = user1, user2
        lg1, lg2 = user1.language, user2.language

        active_user = 2
        u1active = True, False
        logging.info("\n\n\nUser 1 = French\n\n\n\n")
        logging.info(u1)
        logging.info(u2)
        logging.info(1)
    else:
        u1, u2 = user2, user1
        lg1, lg2 = user2.language, user1.language
        u1_active, u2_active = False, True
        active_user = 1
        logging.info("\n\n\nUser 1 = English\n\n\n\n")
        logging.info(u1)
        logging.info(u2)
        logging.info(0)

    # dialogue id - always starts with french user
    dlg_id = timestamp + '_' + lg1 + '_' + lg2 + '_' + u1.idnum + '_' + u2.idnum

    # initialise dialogue and get room number
    room = max([1] + room_numbers) + 1 # room number 1 always taken for hub
    room_numbers.append(room)

    # choose scenario and translation model
    scenario, tmodel = settings.choose_random_scenario()

    # if tmodel has not been chosen above...
    if tmodel is None:
        tmodel = settings.choose_tmodel(u1, u2)
        
    turn_numbers = [1, 2]
    random.shuffle(turn_numbers)

    # choose roles randomly
    if random.random() > 0.5:
        role1_idx = 1
        role2_idx = 2
    else:
        role1_idx = 2
        role2_idx = 1

    logging.info(scenario[role1_idx][1])

    # add new dialogue and update user info
    active_dialogues.add_dialogue(dlg_id, timestamp, lg1, lg2, u1, u2, scenario,
                                  tmodel, turn_numbers, role1_idx, role2_idx, active_user, room)
    u1.add_to_dialogue(dlg_id, scenario[0][1], tmodel, room, scenario[role1_idx][1], turn_numbers[0])
    u2.add_to_dialogue(dlg_id, scenario[0][0], tmodel, room, scenario[role2_idx][0], turn_numbers[1])

    ## add navigator types

    emit('ready_to_chat', {'dialogue_id': dlg_id, 'id_you': id2,
        'name_you': user2.name}, room=all_users.get_user_from_id(id1).sid)
    emit('ready_to_chat', {'dialogue_id': dlg_id, 'id_you': id1,
        'name_you': user1.name}, room=all_users.get_user_from_id(id2).sid)

    # refresh hub for other users
    refresh_hub({'idnum': u1.idnum})

# Log user out manually
@socketio.on('log_user_out', namespace='/')
def log_user_out(message):
    idnum = hashlib.sha256(message["email"].lower().strip().encode('utf-8')).hexdigest()
    user = all_users.get_user_from_id(idnum)
    #logging.info("receive the message")

    # send event to window logged in
    emit('logged_out', {'english': 'You have been logged out by another window.',
                  'french': "Vous avez été déconnecté(e) par une autre fenêtre."},
          room=user.sid, namespace="/hub")
    # send event to window logged in
    emit('logged_out', {'english': 'You have been logged out by another window.',
                  'french': "Vous avez été déconnecté(e) par une autre fenêtre."},
          room=user.sid, namespace="/chat")

    logging.info("Manually logging out:" + str(all_users.get_user_from_id(idnum)) + ":" + str(user.sid))
    # log the user out
    all_users.log_user_out(idnum)



# User joins a chat room
@socketio.on('joined', namespace='/chat')
def joined_chat(message):
    """Sent by clients when they enter a room.
    A status message is broadcast to all people in the room."""
    idnum = session.get('idnum')

    user = all_users.get_user_from_id(idnum)
    # skip if not connected
    if user is None:
        return
    user.sid = request.sid
    room = user.room
    join_room(room)
    all_users.move_user_to_chat(idnum, room)

    session['gender'] = user.gender
    session['language'] = user.language
    session['dialogue_id'] = user.dialogue_id

    dialogue = active_dialogues.get(user.dialogue_id)

    if dialogue is None:
        return
    them = dialogue.get_them(idnum)
    session['them'] = them.name

    if user.language == "english":
        idx=0
        initiated=dialogue.just_initiated0
        dialogue.set_nav_u2(message.get("useragent", None))
    else:
        idx=1
        initiated=dialogue.just_initiated1
        dialogue.set_nav_u1(message.get("useragent", None))

    # tech type for evaluation
    techtype = dialogue.get_tech(idnum)

    emit('scenario', {'their_name': them.name, 'their_gender': them.gender,
                      'their_language': them.language,
                      'your_language': user.language,
                      'your_gender': user.gender,
                      'scenario': dialogue.scenario[0][idx],
                      'role': user.role,
                      'turn_number': user.turn_number,
                      'first_time': initiated,
                      'tech_type': techtype},
                      room=user.sid)

    # if there are already utterances in the dialogue, emit them all!
    emit("empty_messages", {}, room=user.sid)

    eval2idx = {"good": 0, "medium": 1, "bad": 2}

    # this can be the case of a refreshed page
    for utterance in dialogue.utterances:
        sending_user = utterance.user
        receving_user = dialogue.get_them(sending_user.idnum)
        if user.idnum == sending_user.idnum:
            emit('message', {'msg': utterance.original_text,
                             'idnum': utterance.idnum,
                             'name': sending_user.name,
                             'utt_id': utterance.idnum}, room=sending_user.sid)
        elif user.idnum == receving_user.idnum:

            logging.info(eval2idx.get(utterance.eval["judgment"], "None"))

            emit('message', {'msg': utterance.postprocessed_text,
                             'judgment': eval2idx.get(utterance.eval["judgment"], "None"),
                             'eval_problems': utterance.eval["problems"],
                             'verbatim': utterance.eval["verbatim"],
                             'idnum': utterance.idnum,
                             'name': sending_user.name,
                             'utt_id': utterance.idnum}, room=receving_user.sid)
    # set this to False for successive calls
    if idx == 0:
        dialogue.just_initiated0 = False
    else:
        dialogue.just_initiated1 = False


def sentence_splitter(text):
    my_env = os.environ.copy()
    my_env["PERL5LIB"] = config.tooldir+'/alanalyser'
    ps = subprocess.Popen(['echo', bytes(text.strip(), encoding="utf-8")], stdout=subprocess.PIPE, shell=False)
    sents = subprocess.check_output(("perl", config.tooldir+'/alanalyser/alSimpleSentenceSplitter.pl'), stdin=ps.stdout, env=my_env, shell=False).decode('utf-8')
    return sents.split("\n")

def preprocess(sents, config_vars):
    preproc_script = config.preproc_dir + '/preprocess.sh'
    preprocessed = subprocess.check_output(['bash', preproc_script,
                                            "\\n".join(sents),config_vars], shell=False)
    return preprocessed.decode('utf-8').strip().split("\n")

def concat_prev(preprocessed_sents, next_utt_id, dialogue, user):
    # starting symbol
    if len(dialogue.utterances) < 1:
        prev = "<BEGIN> "
    else:
        prev_utterance = dialogue.utterances[next_utt_id - 1]
        # if same language, take the original (preprocessed text)
        if user.language == prev_utterance.user.language:
            prev = prev_utterance.preprocessed_text.split("<CONCAT>")[-1].strip()
        # otherwise take the translation text
        else:
            # if empty and/or not yet translated, take the utterance before that
            if prev_utterance.translated_text == "" and next_utt_id - 2 >= 0 :
                prev = dialogue.utterances[next_utt_id - 2].translated_text.split("<CONCAT>")[-1].strip()
            else:
                prev = prev_utterance.translated_text.split("<CONCAT>")[-1].strip() # last sentence
    # for several sentences, take the previous each time and concatenate
    if len(preprocessed_sents) > 1:
        for idx in range(len(preprocessed_sents[1:])):
            preprocessed_sents[-1-idx] = preprocessed_sents[-2-idx] + " <CONCAT> " + preprocessed_sents[-1-idx]
    preprocessed_sents[0] = prev + " <CONCAT> " + preprocessed_sents[0]
    return preprocessed_sents

def translate(preprocessed_sents, port):
    url = "ws://{0}:{1}{2}".format('localhost', port, '/translate')
    ws = create_connection(url)
    translation = []
    for segment in preprocessed_sents:
        ws.send(segment)
        translation.append(ws.recv())
    ws.close()
    return translation


#def preprocess_and_translate(text, next_utt_id, dialogue, user):


# message sent by chat
@socketio.on('text', namespace='/chat')
def text(data):
    """Sent by a client when the user entered a new message."""

    #logging.info("\n\n"+request.headers.get("encoding")+"\n\n")

    idnum = session.get('idnum')
    dialogue_id = session.get('dialogue_id')
    user = all_users.get_user_from_id(idnum)
    other_user = active_dialogues.get(user.dialogue_id).get_them(idnum)
    name = user.name
    timestamp = datetime.now().isoformat()

    # emit a message to let users know progress
    if other_user.language == "english":
        msg = 'Your partner has sent a message (currently translating…). Make the most of this time to evaluate the sentences already translated!'
        msg2 = 'Votre message est en cours de traduction… Profitez de ce temps pour évaluer les phrases déjà traduites&nbsp;!'
    else:
        msg = 'Votre interlocuteur/trice a envoyé un message (traduction en cours…). Profitez de ce temps pour évaluer les phrases déjà traduites&nbsp;!'
        msg2 = 'Translating your message… Make the most of this time to evaluate the sentences already translated!'
    emit('other_user_sent_msg', {'msg': msg}, room=other_user.sid)
    emit('translating', {'msg': msg2}, room=user.sid)
    socketio.sleep(0)

    # add new utterance
    dialogue = active_dialogues.get(user.dialogue_id)
    text = data['msg'] #bytes(data['msg'].strip(), encoding="iso-8859-1").decode("utf-8") # TODO: fix this
    #utt_id = dialogue.add_utterance(timestamp, text, user)
    preprocessed_sents, translation_text, postprocessed, postprocessed_sents = "", "", "", ""
    pre_time_begin, pre_time_end = (None, None)
    t_time_begin, t_time_end = (None, None)
    post_time_begin, post_time_end = (None, None)
    next_utt_id = len(dialogue.utterances)

    try:
        if True:
            # 0. configuration tools
            t = config.tmodels[dialogue.translation_model]
            if user.language == "english":
                config_vars = t["en2fr_vars"]
                port = t["en2fr_port"]
            else:
                config_vars = t["fr2en_vars"]
                port = t["fr2en_port"]
            logging.info("SELECTED TRANSLATION MODEL: " + config_vars + ", port="+str(port))

            # 0. Sort out encoding problems
            ps = subprocess.Popen(['echo', bytes(text.strip(), encoding="utf-8")], stdout=subprocess.PIPE, shell=False)
            text = subprocess.check_output(("perl", config.preproc_dir+"/alForceUTF8.pl"), stdin=ps.stdout, shell=False).decode('utf-8')
            #text = subprocess.check_output(['perl', config.preproc_dir + "/alForceUTF8.pl"], shell=False).decode("utf-8")

            pre_time_begin = datetime.now().isoformat()
            # 1. split into sentences
            sents = sentence_splitter(text)
            logging.info("before preprocessed = " + "\n".join(sents))
            # 2. pre-process
            preprocessed = preprocess(sents, config_vars)
            logging.info("from preprocessed = " + str(preprocessed))

            # 3. concatenate input if the concatenation model is used
            # Concatenation model - add previous sentence
            # append the previous sentence (in the correct language if the model involves concatenation)
            if t["concat_src"]:
                preprocessed = concat_prev(preprocessed, next_utt_id, dialogue, user)

            pre_time_end = datetime.now().isoformat()
            PLOG(pre_time_end, dialogue_id, user.idnum, "PREPROCESSING", str(preprocessed))

            # 2. Translation
            t_time_begin = datetime.now().isoformat()
            translation = translate(preprocessed, port)
            t_time_end = datetime.now().isoformat()
            logging.warning(str(translation))
            PLOG(t_time_end, dialogue_id, user.idnum, "TRANSLATION", str(translation))

            # 3. Postprocessing
            post_time_begin = datetime.now().isoformat()
            postprocessed = subprocess.check_output(['bash', config.preproc_dir + '/postprocess.sh',
                "\\n".join(translation), config_vars], shell=False).decode("utf-8") #\\

            postprocessed_sents = [x for x in postprocessed.split("\n") if x.strip() != ""]
            #postprocessed = postprocessed.replace("\n", " ")
            post_time_end = datetime.now().isoformat()
            PLOG(post_time_end, dialogue_id, user.idnum, "POSTPROCESSED", postprocessed.strip())
        else:
            sents = [text]
            translation = [text]
            preprocessed = [text]
            postprocessed_sents = [text]

        # now stock all utterances separately
        for i, p in enumerate(postprocessed_sents):
            utt_id = dialogue.add_utterance(timestamp, sents[i], user)
            # emit original message to sender and translated message to other client
            emit('message', {'msg': sents[i], 'idnum': idnum, 'name': name,
                             'utt_id': utt_id}, room=user.sid)
            emit('message', {'msg': str(postprocessed_sents[i]), 'idnum': idnum, 'name': name,
                             'utt_id': utt_id}, room=other_user.sid)
            sent_time = datetime.now().isoformat()
            utterance = active_dialogues.get(dialogue_id).utterances[utt_id]
            utterance.set_translation(preprocessed[i], translation[i], postprocessed_sents[i],
                                      pre_time_begin, pre_time_end, t_time_begin,
                                      t_time_end, post_time_begin, post_time_end,
                                      sent_time)

        # emit a message to let users know progress
        emit('finished_translation', {}, room=user.sid)

        # how many utterances each? If at least 10 each, let them know that the
        # minimum has been reached
        if active_dialogues.get(dialogue_id).minimum_nb_utterances(15):
            english_msg = "You have reached the minimum number of utterances per person (15). You can of course continue this dialogue if you wish! Once you are ready, go to the final evaluation step by clicking on \'end this dialogue\'. You may then start a new dialogue of you wish."
            french_msg = "Vous avez atteint le nombre minimum recommandé d'énoncés par personne dans un dialogue (15). Vous pouvez bien sûr continuer si vous voulez ! Une fois que vous êtes prêt(e), passez à l'étape d'évaluation finale en cliquant sur 'finir ce dialogue'. Ensuite, vous pouvez faire un autre dialogue si vous le souhaitez."
            emit("minimum-reached", {"english": english_msg, "french": french_msg}, room=user.sid)
            emit("minimum-reached", {"english": english_msg, "french": french_msg}, room=other_user.sid)

        # dump dialogue
        active_dialogues.get(dialogue_id).dump_dialogue()
    except Exception or Error as e:
        emit("translation-error", {"error":str(e)},room=user.sid)
        emit("translation-error", {"error":str(e)}, room=other_user.sid)
        PLOG(t_time_end, dialogue_id, user.idnum, "PREPROCESSING/TRANSLATION/POSTPROCESSING ERROR", str(e))



@socketio.on('leave_dialogue', namespace='/chat')
def leave_dialogue(message):
    """Sent by clients when they leave a room."""
    idnum = idnum = session.get('idnum')
    user = all_users.get_user_from_id(idnum)
    other_user = active_dialogues.get(user.dialogue_id).get_them(idnum)
    dialogue = active_dialogues.dialogues[user.dialogue_id]

    # Set to eval-stage
    active_dialogues.dialogues[user.dialogue_id].set_eval(idnum)

    if other_user.language == "english":
        msg = "The other user has ended the dialogue. PLEASE DO NOT CLOSE THE WINDOW YET. Once you are ready, go to the final evaluation step by clicking on \'end this dialogue\'."
    else:
        msg = "Le dialogue a été terminé. NE FERMEZ PAS ENCORE CETTE FENÊTRE S'IL VOUS PLAÎT. Une fois que vous êtes prêt(e), passez à l'étape d'évaluation finale en cliquant sur 'finir ce dialogue'."
    # take other user out of the room too if not already finished

    if other_user.room == dialogue.room and dialogue.get_eval(other_user.idnum) == False:
        emit('abandoned', {'msg': msg},
            room=other_user.sid)
    # leave room
    #leave_room(user.room)
    #user.dialogue_id = None
    #if "log_out" not in message:
    #    all_users.move_user_back_to_hub(idnum)
    # delete dialogue

@socketio.on('passively_left', namespace='/chat')
def passively_left(data):
    idnum = session.get('idnum')
    user = all_users.get_user_from_id(idnum)
    leave_room(user.room)
    all_users.move_user_back_to_hub(user.idnum)
    dialogue_id = user.dialogue_id

    # for now end dialogue here TODO: evaluation after dialogue
    #active_dialogues.close_dialogue(dialogue_id)
    #user.dialogue_id = None


# Smiley has been clicked. Note the change in evaluation
@socketio.on('eval-smiley', namespace='/chat')
def evaluation(data):
    dlg_id = session.get('dialogue_id')
    utt_id = data['utt_id']
    evaluation = {0: "good", 1: "medium", 2: "bad"}.get(data['idx'])
    timestamp = datetime.now().isoformat()#strftime("%Y-%m-%d--%H-%M-%S", gmtime())
    active_dialogues.get(dlg_id).add_evaluation(utt_id, evaluation, timestamp)


# Problem has been checked/unchecked. Note the change in evaluation
@socketio.on('eval-problemtype', namespace='/chat')
def evaluation_problem(data):
    dlg_id = session.get('dialogue_id')
    utt_id = data['utt_id']
    prob = data["problem"]
    timestamp = datetime.now().isoformat()#strftime("%Y-%m-%d--%H-%M-%S", gmtime())
    if data["value"] == "yes":
        value = True
    elif data["value"] == "no":
        value = False
    active_dialogues.get(dlg_id).change_problem(utt_id, prob, value, timestamp)

# Verbatim input for evaluation. Note the change in evaluation
@socketio.on('verbatim_change', namespace='/chat')
def verbatim_change(data):
    dlg_id = session.get('dialogue_id')
    utt_id = data['utt_id']
    value = data['value']
    timestamp = datetime.now().isoformat()#strftime("%Y-%m-%d--%H-%M-%S", gmtime())
    active_dialogues.get(dlg_id).add_verbatim(int(utt_id), value, timestamp)

# Client is typing
@socketio.on('typing', namespace='/chat')
def typing(data):
    idnum = idnum = session.get('idnum')
    user = all_users.get_user_from_id(idnum)
    other_user = active_dialogues.get(user.dialogue_id).get_them(idnum)


    if other_user.language == "english":
        msg = "Your partner is typing… Make the most of this time to evaluate the sentences already translated!"
    else:
        msg = "Votre interlocuteur/trice est en train d'écrire… Profitez de ce temps pour évaluer les phrases déjà traduites&nbsp;!"
    # show that the user is typing
    emit('other_user_typing', {"msg": msg},
            room=other_user.sid)

# Client has stopped typing
@socketio.on('stopped_typing', namespace='/chat')
def stopped_typing(data):
    idnum = idnum = session.get('idnum')
    user = all_users.get_user_from_id(idnum)
    other_user = active_dialogues.get(user.dialogue_id).get_them(idnum)

    if other_user.language == "english":
        msg = "Your partner is typing…"
    else:
        msg = "Votre interlocuteur/trice est en train d'écrire…"

    # show that the user has stopped typing
    emit('other_user_stopped_typing', {"typing_text": msg}, room=other_user.sid)

@socketio.on('eval-tech-value', namespace="/chat")
def eval_tech_type(data):
    user = all_users.get_user_from_id(data["idnum"])
    if user is None:
        return
    dialogue = active_dialogues.dialogues.get(user.dialogue_id, None)
    if dialogue is None:
        return
    dialogue.set_tech(data["techtype"], user.idnum)


@socketio.on('joined_transcription', namespace='/transcription')
def joined_transcription(data):
    idnum = idnum = data["idnum"]
    session_id = request.sid
    user = all_users.get_user_from_id(idnum)
    if user is None:
        return
    dialogue = active_dialogues.get(user.dialogue_id)
    if dialogue is None:
        return

    transcript = dialogue.get_transcript(user.language)
    logging.info(transcript)
    emit('receive_transcription', {'utterances': transcript}, room=session_id)
