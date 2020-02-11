import os
import json
from collections import OrderedDict
import app.config as config
import logging

class Dialogues():
    def __init__(self):
        self.dialogues = {}

    def add_dialogue(self, idnum, timestamp, lg1, lg2, user1, user2, scenario,
                     tmodel, turn_numbers, role1, role2, active_user, room):
        self.dialogues[idnum] = Dialogue(idnum, timestamp, lg1, lg2,
            user1, user2, scenario, tmodel, turn_numbers, role1, role2,
            active_user, room)
        os.sys.stderr.write("New dialogue added: " + str(self.dialogues) +"\n")

    def get(self, idnum):
        return self.dialogues.get(idnum, None)

    def close_dialogue(self, idnum):
        self.dialogues[idnum].dump_dialogue()
        del self.dialogues[idnum]


class Dialogue():
    def __init__(self, idnum, start_timestamp, lg1, lg2, user1, user2,
            scenario, translation_model, turn_numbers, role1, role2,
            active_user, room):
        self.idnum = idnum
        self.start_timestamp = start_timestamp
        self.end_timestamp = None

        self.lang1 = lg1
        self.lang2 = lg2

        self.user1 = user1
        self.user2 = user2

        self.room = room

        if active_user == 1:
            user1_active, user2_active = True, False
        elif active_user == 2:
            user1_active = user2_active = False, True
        self.user1_info = {"role_num": role1, "role": scenario[role1],
                           "lang": lg1, "turn_number": turn_numbers[0],
                           "initiated_dialogue": user1_active,
                           "eval-stage": False}
        self.user2_info = {"rolenum": role2, "role": scenario[role2],
                           "lang": lg2, "turn_number": turn_numbers[1],
                           "initiated_dialogue": user2_active,
                           "eval-stage": False}

        self.just_initiated1 = True
        self.just_initiated0 = True

        self.tech_eval1 = None
        self.tech_eval2 = None
        
        # turn into a list of languages in order of turns, depending on who is assigned the first turn
        #if turn_numbers[0] == user1.idnum:
        #    self.first_turn = "user1"
        #    self.second_turn = "user2"
        #else:
        #    self.first_turn = "user2"
        #    self.second_turn = "user1"

        # roles of user 1 and user2
        #self.user1_role = role1
        #self.user2_role = role2

        self.translation_model = translation_model
        self.scenario = scenario # user1 = scenario[1], user2 = scenario[2]

        self.utterances = []
        self.nb_utterances = 0

        self.final_eval1 = {}
        self.final_eval2 = {}

        self.eval_stage = False


    def set_nav_u1(self, useragent):
        self.user1_info["useragent"] = useragent

    def set_nav_u2(self, useragent):
        self.user2_info["useragent"] = useragent
        
    def set_tech(self, techtype, user_idnum):
        if self.user1.idnum == user_idnum:
            self.tech_eval1 = techtype
        elif self.user2.idnum == user_idnum:
            self.tech_eval2 = techtype

    def get_tech(self, user_idnum):
        if self.user1.idnum == user_idnum:
            return self.tech_eval1
        elif self.user2.idnum == user_idnum:
            return self.tech_eval2
        
    def set_eval(self, user_idnum):
        if self.user1.idnum == user_idnum:
            self.user1_info["eval-stage"] = True
        elif self.user2.idnum == user_idnum:
            self.user2_info["eval-stage"] = True

    def get_eval(self, user_idnum):
        if self.user1.idnum == user_idnum:
            return self.user1_info["eval-stage"]
        elif self.user2.idnum == user_idnum:
            return self.user2_info["eval-stage"]
        else:
            return None
            
        
    def get_transcript(self, language):
        utts = []
        for utterance in self.utterances:
            if utterance.original_language == language:
                utts.append({'text': utterance.original_text,
                             'language': language})
            else:
                utts.append({'text': utterance.postprocessed_text,
                             'language': utterance.original_language})
        return utts

    def minimum_nb_utterances(self, minimum):
        nb = [0,0]
        logging.info("\n\n"+str(len(self.utterances))+"\n\n")
        for utt in self.utterances:
            if utt.user.idnum == self.user1.idnum:
                nb[0] += 1
            else:
                nb[1] += 1

        logging.info("\n\n"+str(nb)+"\n\n")
        return min(nb) >= minimum

    def __str__(self):
        txt = "Dialogue:\n"
        txt += "Scenario: " + str(self.scenario)
        for utterance in self.utterances:
            txt += str(utterance)
        return txt

    def add_utterance(self, timestamp, text, user):
        utt = Utterance(timestamp, text, user, self.idnum, self.nb_utterances)
        self.utterances.append(utt)
        self.nb_utterances += 1
        return self.nb_utterances-1

    def add_evaluation(self, utterance_id, evaluation, timestamp):
        rvalue = self.utterances[utterance_id].evaluation(evaluation, timestamp)
        if rvalue:
            self.dump_dialogue()

    def change_problem(self, utterance_id, problem, value, timestamp):
        self.utterances[utterance_id].change_problem(problem, value, timestamp)
        self.dump_dialogue()

    def get_them(self, id_me):
        os.sys.stderr.write("id1 = " + self.user1.idnum +", id2 = " + self.user2.idnum + "\n\n")
        if id_me == self.user1.idnum:
            return self.user2
        elif id_me == self.user2.idnum:
            return self.user1
        else:
            Exception('The user is not a member of this dialogue')

    def dump_dialogue(self):
        dialogue = OrderedDict()
        for el in [('start_time', self.start_timestamp),
                    ('end_time', self.end_timestamp),
                    ('scenario', self.scenario),
                    ('user1', self.user1_info),
                    ('user2', self.user2_info),
                    ('translation_model', self.translation_model),
                    ('utterances', {})]:
            dialogue[el[0]] = el[1]

        # add utterances
        for utterance in self.utterances:
            dialogue['utterances'][utterance.idnum] = utterance.dumpable_format()

        # added final evaluation forms
        dialogue["final_evaluation_user1"] = self.final_eval1
        dialogue["final_evaluation_user2"] = self.final_eval2

        filepath = config.dialogue_dir + "/" + self.idnum + '.json'
        json.dump(dialogue, open(filepath, 'w'), indent=2)

    def add_verbatim(self, utt_id, value, timestamp):
        rvalue = self.utterances[utt_id].add_verbatim(value, timestamp);
        if rvalue:
            self.dump_dialogue()

    def add_final_evaluation(self, idnum, timestamp, form):
        assert(idnum in [self.user1.idnum, self.user2.idnum])
        if idnum == self.user1.idnum:
            self.final_eval1 = form
            self.final_eval1["timestamp"] = timestamp
            for key in ["csrf_token", "login"]:
                del self.final_eval1[key]
        else:
            self.final_eval2 = form
            self.final_eval2["timestamp"] = timestamp
            for key in ["csrf_token", "login"]:
                del self.final_eval2[key]
        self.dump_dialogue()

class Utterance():

    def __init__(self, timestamp, text, user, dialogue_id, utterance_id, turn_num=1):
        self.idnum = utterance_id
        self.dialogue_id = dialogue_id
        self.user = user
        self.original_text = text
        self.translated_text = ""
        self.preprocessed_text = ""
        self.postprocessed_text = ""
        self.turn_num = turn_num
        self.original_language = user.language

        # timestamps saved
        self.composition_timestamp = timestamp
        self.preprocessing_begin_end = (None, None)
        self.translation_begin_end = (None, None)
        self.postprocessing_begin_end = (None, None)
        self.translated_begin_end = (None)
        self.sent_timestamp = None

        self.eval = {"judgment": None, "problems": [], "verbatim": "",
                    "judgment_history": [], "problem_history":[], "verbatim_history":[]}


    def __str__(self):
        txt = str(self.idnum) + ": \n"
        txt += "\tOriginal: " + self.original_text + "\n"
        txt += "Translation: " + self.postprocessed_text + "\n"
        return txt

    def evaluation(self, judgment, timestamp):
        # only change if different
        if self.eval["judgment"] != judgment:
            self.eval["judgment"] = judgment
            self.eval["judgment_history"].append( (judgment, timestamp) )
            return True
        return False

    def change_problem(self, problem, value, timestamp):
        if value and problem not in self.eval["problems"]:
            self.eval["problems"].append(problem)
        elif not value and problem in self.eval["problems"]:
            self.eval["problems"].remove(problem)

        self.eval["problem_history"].append( (problem, timestamp, value) )

    def add_verbatim(self, value, timestamp):
        if self.eval["verbatim"] != value:
            self.eval["verbatim_history"].append((value, timestamp, timestamp))
            self.eval["verbatim"] = value
            return True
        return False

    def set_translation(self, preprocessed, translation, postprocessed,
                        pre_time_begin, pre_time_end, t_time_begin, t_time_end,
                        post_time_begin, post_time_end, sent_timestamp):
        self.preprocessed_text = preprocessed
        self.translated_text = translation
        self.postprocessed_text = postprocessed
        self.preprocessing_begin_end = (pre_time_begin, pre_time_end)
        self.translation_begin_end = (t_time_begin, t_time_end)
        self.postprocessing_begin_end = (post_time_begin, post_time_end)
        self.sent_timestamp = sent_timestamp

    def dumpable_format(self):
        return OrderedDict([('language', self.user.language),
                ('original_text', self.original_text),
                ('preprocessed_text', self.preprocessed_text),
                ('translated_text', self.translated_text),
                ('postprocessed_text', self.postprocessed_text),
                ('composition_time', self.composition_timestamp),
                ('preprocessing_begin', self.preprocessing_begin_end[0]),
                ('preprocessing_end', self.preprocessing_begin_end[1]),
                ('translation_begin', self.translation_begin_end[0]),
                ('translation_end', self.translation_begin_end[1]),
                ('postprocessing_begin', self.postprocessing_begin_end[0]),
                ('postprocessing_end', self.postprocessing_begin_end[1]),
                ('sent_time', self.sent_timestamp),
                ('eval', self.eval)
                 ])
