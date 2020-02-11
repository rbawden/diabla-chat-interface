from flask_login import LoginManager, UserMixin#, login_required, login_user, logout_user
import os, json
import base64
import app.config as config
import time
import logging
from datetime import datetime
import hashlib


def pad(text_bytes):
    while len(text_bytes) % 8 != 0:
        text_bytes += b' '
    return text_bytes


class User(UserMixin):

    def __init__(self, language, name, idnum):

        self.name = name
        self.age = None
        self.gender = None
        self.sid = None
        self.ready_to_chat = False
        self.role = None
        self.language = language
        self.checked_confirmation = True

        self.idnum = idnum

        # keep a track of user dialogue history
        self.past_dialogues = []
        self.past_models = {}
        self.past_scenarios = []

        # load from file
        self.load_form_details()

        self.ping = time.time()
        self.room = 1 # 1 = hub
        self.dialogue_id = None
        self.alert = False

    def number_times_tmodel(self, tmodel_name):
            return self.past_models.get(tmodel_name, 0)

    def load_form_details(self):
        # load details
        with open(config.user_dir + '/' + self.idnum + '.json', 'r') as out:
            loaded = json.load(out)
        # get certain values only
        self.past_dialogues = loaded['past_dialogues']
        self.past_models = loaded['past_models']
        self.past_scenarios = loaded['past_scenarios']
        self.gender = loaded['gender']

    def dump_details(self):
        logging.warn("Dumping user details")
        with open(config.user_dir + '/' + self.idnum + '.json', 'r') as out:
            form_details = json.load(out)

        # update these fields
        form_details["past_dialogues"] = self.past_dialogues
        form_details["past_models"] = self.past_models
        form_details["past_scenarios"] = self.past_scenarios
        #form_details["checked_confirmation"] = self.checked_confirmation

        with open(config.user_dir + '/' + self.idnum + '.json', 'w') as out:
            json.dump(form_details, out, indent=2)

    def pinged(self, source="chat"):
        logging.warn("Ping from "+str(self))
        self.ping = time.time()

    def return_key(self):
        return self.id

    def add_to_dialogue(self, dialogue_id, scenario, tmodel, room, role, turn_number):
        self.room = room
        self.dialogue_id = dialogue_id
        self.turn_number = turn_number # 1 = starts dialogue, 2 = doesn't start
        self.role = role
        self.past_dialogues.append((dialogue_id, tmodel, scenario, role, turn_number))
        if tmodel not in self.past_models:
            self.past_models[tmodel] = 0
        self.past_models[tmodel] += 1
        self.dump_details()

    def __str__(self):
        return self.name + " (" + self.idnum + ", room=" + str(self.room) + ")"


# User class to keep a track of all online users
class Users():
    def __init__(self):
        self.online_users = {}
        self.hub_users = {}

    def __str__(self):
        text = "Users:\n"
        for idnum in self.online_users:
            text += "\t" + str(self.online_users[idnum]) + "\n"
        return text

    def number_users(self, language):
        return len([1 for x in self.online_users if self.online_users[x].language == language])
    
    def all_hub_users(self):
        return self.hub_users

    def get_number_online(self):
        return len(self.online_users)

    #def get_email_from_id(self, idnum):
    #    if idnum in self.online_users:
    #        return self.online_users[idnum].email
    #    else:
    #        return None

    #def get_user_from_email(self, email):
    #    logging.info(email)
    #    for idnum in self.online_users:
    #        if self.decrypt_idnum(idnum) == email:
    #            return self.online_users[idnum]
    #    return None

    def get_user_from_id(self, idnum):
        if idnum in self.online_users:
            return self.online_users[idnum]
        else:
            return None

    def encrypt_email(self, email):
        return hashlib.sha256(email.encode('utf-8')).hexdigest()


    def ascii_id(self, idnum):
        text = ''
        for char in idnum:
            text += '&#' + str(ord(char)) + ';'
        return text

    def de_ascii_id(self, text):
        idnum = ''
        current = ''
        for char in text:
            current += char
            if char == ';':
                idnum += chr(int(current[2:-1]))
                current = ''
        return idnum

    def add_user(self, email, language, name):
        idnum = self.encrypt_email(email)
        self.online_users[idnum] = User(language, name, idnum)
        self.hub_users[idnum] = self.online_users[idnum]
        logging.warn(str(self))

        return idnum

    def move_user_to_chat(self, idnum, room):
        # might not be in hub users if refreshing chat
        self.online_users[idnum].room = room
        if idnum in self.hub_users:
            del self.hub_users[idnum]

    def move_user_back_to_hub(self, idnum):
        self.hub_users[idnum] = self.online_users[idnum]
        self.online_users[idnum].room = 1

    def change_sid(self, idnum, sid):
        self.online_users[idnum].sid = sid

    def remove_user(self, idnum):
        # update details before removing
        if idnum not in self.online_users:
            return
        
        self.online_users[idnum].dump_details()

        # terminate dialogues currently running
        #dialogue_id = self.online_users[idnum].dialogue_id

        # remove from list of users
        if idnum in self.hub_users:
            del self.hub_users[idnum]
        del self.online_users[idnum]

    def get_list_users(self):
        return self.online_users

    def get_list_users_all(self):
        users = [self.online_users[x] for x in self.online_users]
        langs = [x.language for x in users]
        idnums = [x.idnum for x in users]
        names = [x.name for x in users]
        rooms = [x.room for x in users]
        for user in users:
            logging.info(user.name + " - " + str(user.room))

        return idnums, names, langs, rooms

    def get_list_names(self, lower=True):
        if lower:
            users = [self.online_users[x].name.lower() for x in self.online_users]
        else:
            users = [self.online_users[x].name for x in self.online_users]
        return users

    #def get_list_emails(self):
    #    users = [self.online_users[x].email for x in self.online_users]
    #    return users

    def get_list_idnums(self):
        users = [idnum for idnum in self.online_users]
        return users

    def get_other_lang_user_ids(self, language):
        return [x for x in self.online_users if self.online_users[x].language != language]

    def get_other_lang_user_names(self, language):
        return [self.online_users[x].name for x in self.online_users \
            if self.online_users[x].language != language]

    def log_user_out(self, idnum):
        logging.info("IN LOG USER OUT")

        self.remove_user(idnum)

    def cleanup(self):
        logging.info("IN CLEANUP")
        idnums = list(self.online_users.keys())
        logging.info(self.online_users)
        dialogues_to_end = []
        users_removed = []
        current = time.time()
        for idnum in list(idnums):
            user = self.get_user_from_id(idnum)
            if user is None:
                continue
            name = user.name

            hub_delay = 120
            chat_delay = 300
            logging.info(name + ":" +str(user.ping))

            # if user has clearly disappeared, remove them
            if user is None:
                #self.remove_user(idnum)
                users_removed.append(idnum)

            elif user.alert:
                if (user.room == 1 and current - user.ping > hub_delay*2) or \
                    (user.room != 1 and current - user.ping > chat_delay*2):
                    logging.info("Disconnected user after no ping > " + str(chat_delay*2) + " seconds: " + name)
                    logging.info("Or disconnected user after no ping > " + str(hub_delay**2) + " seconds: " + name)
                    logging.info(current - user.ping)
                    if user.dialogue_id is not None:
                        dialogues_to_end.append(user.dialogue_id)
                    users_removed.append(idnum)

            elif user.room == 1 and (current - user.ping > hub_delay):
                logging.info("Disconnected user after no ping > " + str(hub_delay) + " seconds: " + name)
                logging.info(current - user.ping)
                if user.dialogue_id is not None:
                    dialogues_to_end.append(user.dialogue_id)
                #self.remove_user(idnum)
                users_removed.append(idnum)

            elif user.room != 1 and (current - user.ping > chat_delay):
                logging.info("Disconnected user after no ping > " + str(chat_delay) + " seconds: " + name)
                logging.info(current - user.ping)
                # check to see whether we need to close a dialogue or not
                if user.dialogue_id is not None:
                    dialogues_to_end.append(user.dialogue_id)
                #self.remove_user(idnum)
                users_removed.append(idnum)


            elif current - user.ping > chat_delay and current - user.ping > hub_delay:
                logging.info("Disconnected user after no ping > " + str(hub_delay) + " seconds: " + name)
                logging.info(current - user.ping)
                if user.dialogue_id is not None:
                    dialogues_to_end.append(user.dialogue_id)
                #self.remove_user(idnum)
                users_removed.append(idnum)

        return users_removed, dialogues_to_end
