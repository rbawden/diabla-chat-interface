#! coding: utf-8
from flask_wtf import FlaskForm
import wtforms.fields as wtff
import wtforms.validators as wtfv
from wtforms_components import Email
from datetime import date, datetime
from app.main.variables import *
import os
from app import socketio, all_users
import app.config as config
import logging
import re
import hashlib

class MyRequired(wtfv.DataRequired):
    field_flags = ('required',)

    def __init__(self, form, field, *args, **kwargs):
        en_txt = "This field is required. "
        fr_txt = "Ce champ est requis. "
        if field.data is None or field.data == "":
            logging.warn("did not validate properly")
            raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})
            raise wtfv.StopValidation()

class MyEmail(wtfv.Email):
    def __init__(self, form, field, *args, **kwargs):
        try:
             super(MyEmail, self).__call__(form, field)
        except wtfv.ValidationError:
            en_txt = "Invalid format. "
            fr_txt = "Format invalide. "
            raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})
            raise wtfv.StopValidation()

def validate_email(form, field):

    if field.data is None:
        en_txt =  "Servor error. Please try again"
        fr_txt =  "Erreur du serveur. Merci de re-essayer."
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

    if not re.match("^[a-zA-Z_\-0-9\.]+@[a-zA-Z_\-0-9\.]+$", field.data.lower()):
        en_txt = 'Invalid format. '
        fr_txt = 'Format invalide. '
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

    idnum = hashlib.sha256(field.data.lower().strip().encode('utf-8')).hexdigest()

    if not os.path.exists(config.user_dir + '/'+idnum + '.json'):
        en_txt = 'This email address has not been registered yet. '
        fr_txt = 'Cette adresse e-mail n\'a pas encore été enregistrée. '
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})
    if idnum in all_users.get_list_idnums():
        raise wtfv.ValidationError({"english":'You are already logged in somewhere else. \
        Please log out in the other window or wait 5 minutes.',
        "french": "Vous êtes déjà connecté(e) ailleurs. Merci de fermer l'autre fenêtre ouverte ou d'attendre 5 minutes. "})

def validate_new_email(form, field):

    if field.data in ["", None]:
        return # ignore - Required validation will take care of this

    idnum = hashlib.sha256(field.data.lower().strip().encode('utf-8')).hexdigest()

    if not re.match("^[a-zA-Z_\-0-9\.]+@[a-zA-Z_\-0-9\.]+$", field.data.strip().lower()):
        en_txt = 'Invalid format. '
        fr_txt = 'Format invalide. '
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

    if field.data != "" and os.path.exists(config.user_dir + '/' + idnum + '.json'):
        en_txt = 'This email address has already been registered. '
        fr_txt = 'Cet adresse e-mail a déjà été enregistrée. '
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

def valid_input_text(form, field):
    if field.data is None:
        en_txt =  "Servor error. Please try again"
        fr_txt =  "Erreur du serveur. Merci de re-essayer."
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})
    field.data = re.sub("`'’‘'", "'", field.data.strip().lower())
    field.data = re.sub("‹›«»“”", '"', field.data)
    if not re.match("^[a-zA-Z0-9 \n\r\téàèêëîïÉÀÈÎÏÔÖÆæçÇöôœøŒØÑñńŃÂÁÄÃãáâāåûüúùÙÜÚŪ°%_.\/\-\'\!\?\"\(\)\,\;\:£$¥€\+]+$", field.data):
        en_txt = "Invalid format. Only alphanumeric, certain punctuation marks and space characters are allowed."
        fr_txt = "Format invalide. Seuls les lettres, les chiffres, certains signes de ponctuation et l'espace sont autorisés."
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

# Validate date to make sure the client is over 18 and is of a valid age
def validate_age(form, field):
    en_txt = ("Invalid age. ",
              "You appear to be older than the oldest living person. This is not possible. ",
              'You must be 18 to register. ')
    fr_txt = ("Âge invalide",
              "Vous semblez être plus âgé(e) que la personne la plus vieille au monde. Ceci n'est pas possible. ",
            "Vous devez avoir au moins 18 ans pour créer un compte. ")
    if field.data is not None:
        age = int(field.data)
        if age < 18:
            raise wtfv.ValidationError({"english": en_txt[2], "french": fr_txt[2]} )
        elif age < 0:
            raise wtfv.ValidationError({"english": en_txt[0], "french": fr_txt[0]} )
        elif age > 117:
            raise wtfv.ValidationError({"english": en_txt[1], "french": fr_txt[1]} )



def validate_name(form, field):

    if field.data is None:
        en_txt =  "Servor error. Please try again. "
        fr_txt =  "Erreur du serveur. Merci de re-essayer. "
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

    field.data = re.sub("`'’‘'", "'", field.data.strip())

    if field.data != "" and field.data.lower() in all_users.get_list_names():
        en_txt = "This username has already been taken by somebody connected. Please choose another one."
        fr_txt = "Ce nom d'utilisateur est déjà pris. Merci d'en choisir un autre."
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

    elif not re.match("^[a-zA-Z0-9 éàèêëîïÉÀÈÎÏÔÖöôœøÆæçÇŒØÑñńŃÂÁÄÃãáâāåûüúùÙÜÚŪ%_.\-\']+$", field.data.lower()):
        en_txt = "Invalid format. Only alphanumeric, certain punctuation marks and space characters are allowed."
        fr_txt = "Format invalide. Seuls les lettres, les chiffres, certains signes de ponctuation et l'espace sont autorisés."
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

def validate_confirmation(form, field):
    en_txt = 'This box must be checked to register.'
    fr_txt = 'Cette case doit être cochée.'
    if not field.data:
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

class MyLength15():
    def __init__(self, form, field,*args, **kwargs):
        if field.data is None:
            en_txt =  "Servor error. Please try again"
            fr_txt =  "Erreur du serveur. Merci de réessayer."
            raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

        if len(field.data) > 15:
            en_txt = "15 characters maximum. "
            fr_txt = "15 caractères maximum. "
            raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

class MyLength100():
    def __init__(self, form, field,*args, **kwargs):
        if field.data is None:
            en_txt =  "Servor error. Please try again"
            fr_txt =  "Erreur du serveur. Merci de réessayer."
            raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

        if len(field.data) > 100:
            en_txt = "100 characters maximum. "
            fr_txt = "100 caractères maximum. "
            raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

class MyLength3000():
    def __init__(self, form, field,*args, **kwargs):
        if field.data is None:
            en_txt =  "Servor error. Please try again"
            fr_txt =  "Erreur du serveur. Merci de réessayer."
            raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})


        if len(field.data) > 3000:
            en_txt = "3000 characters maximum. "
            fr_txt = "3000 caractères maximum. "
            raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

class MyLength1000():
    def __init__(self, form, field,*args, **kwargs):
        if field.data is None:
            en_txt =  "Servor error. Please try again"
            fr_txt =  "Erreur du serveur. Merci de réessayer."
            raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

        if len(field.data) > 1000:
            en_txt = "1000 characters maximum. "
            fr_txt = "1000 caractères maximum. "
            raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

class LoginForm(FlaskForm):
    name = wtff.StringField('Username', validators=[MyRequired,
                                                    validate_name,
                                                    MyLength15])
    email = wtff.StringField('Email', validators=[MyRequired,
                                                  validate_email,
                                                  MyLength100])
    language = wtff.SelectField(u'Language', choices=[('english', 'English'),
                                                 ('french', 'French')],
                                              validators=[MyRequired])
    login = wtff.SubmitField('Log in')


class NewAccountForm(FlaskForm):
    """More detailed form"""
    email = wtff.StringField('Email', validators=[MyRequired,
                                                  wtfv.Email({"english": "Invalid format.",
                                                  "french": "Format invalide."}),
                                                  validate_new_email,
                                                  MyLength100])
    age = wtff.SelectField('Age in years',
                            choices=[('18-24', '18-24'),
                                      ('25-34', '25-34'),
                                      ('35-44', '35-44'),
                                      ('45-54', '45-54'),
                                      ('55-64', '55-64'),
                                      ('65-74', '65-74'),
                                      ('75-84', '75-84'),
                                      ('85-94', '85-94'),
                                      ('95-104', '95-104'),
                                      ('105-114', '105-114')],
                            validators=[MyRequired])
    gender = wtff.SelectField({"english": 'Gender', "french": "Sexe"},
                        choices=[('f', 'Female/Féminin'),('m', 'Male/Masculin')],
                         validators=[MyRequired],
                         description={'disabled':''})
    english_ability = wtff.SelectField({"english": 'English language ability',
                                        "french": "Niveau d'anglais"},
                          choices=[('nat', 'Native/Natif'), ('near', 'Near-native/Quasi-natif'),
                                    ('good', 'Good/Bon'), ('medium', 'Medium/Intermédiaire'),
                                    ('poor', 'Beginner/Débutant'),('none', 'None/Aucun')],
                                    validators=[MyRequired])
    french_ability = wtff.SelectField({"english": 'French language ability',
                                     "french": "Niveau de français"},
                          choices=[('nat', 'Native/Natif'), ('near', 'Near-native/Quasi-natif'),
                                    ('good', 'Good/Bon'), ('medium', 'Medium/Intermédiaire'),
                                    ('poor', 'Beginner/Débutant'),('none', 'None/Aucun')],
                                    validators=[MyRequired],
                                    description={'disabled':''})
    otherlangs = wtff.StringField({"english": 'Other languages spoken',
                                  "french": "Autres langues parlées"},
                                   validators=[wtfv.Optional(),valid_input_text, MyLength1000])
    tal = wtff.BooleanField('TAL', validators=[])
    research = wtff.BooleanField('research', validators=[])
    confirmation = wtff.BooleanField('Confirmation', validators=[validate_confirmation])
    register = wtff.SubmitField('Ok')

def not_none(form, field):
    en_txt = 'This field is required'
    fr_txt = 'Ce champ est obligatoire'
    if field.data is None or field.data == "None":
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})

def required_if_tech_ok(form, field):
    en_txt = 'This field is required'
    fr_txt = 'Ce champ est obligatoire'
    if form.data["tech"] == "ok" and field.data == "":
        raise wtfv.ValidationError({"english": en_txt, "french": fr_txt})
    else:
        raise wtfv.StopValidation()

class RequiredIf(wtfv.DataRequired):
    """Validator which makes a field required if another field is set and has a truthy value.

    Sources:
        - http://wtforms.simplecodes.com/docs/1.0.1/wtfv.html
        - http://stackoverflow.com/questions/8463209/how-to-make-a-field-conditionally-optional-in-wtforms

    """
    field_flags = ('requiredif',)

    def __init__(self, other_field_name, values, message=None, *args, **kwargs):
        self.other_field_name = other_field_name
        self.message = message
        self.values = values

    def __call__(self, form, field):
        other_field = form[self.other_field_name]
        if other_field is None:
            raise Exception('no field named "%s" in form' % self.other_field_name)
        if other_field.data in self.values:
            super(RequiredIf, self).__call__(form, field)
        else:
            wtfv.Optional().__call__(form, field)

# Function below not corrected/updated for string wordings
class EvaluationForm(FlaskForm):
    en_txt = 'Were there any technical problems with the dialogue?'
    fr_txt = 'Avez-vous rencontré des problèmes pratiques au cours du dialogue&nbsp;?'
    tech = wtff.RadioField(en_txt,
                       choices = [('absent', 'The other person was absent.'),
                                   ('nocoop', 'The other person did not cooperate with me.'),
                                   ('techprob', 'There was a technical problem with the application.'),
                                   ('ok', 'None of the above.')],
                       validators=[MyRequired])
    en_txt = "Coherence"
    coherence = wtff.RadioField(en_txt,
                                choices=[('excellent', 'Excellent'),
                                         ('good' ,'Good'),
                                         ('ave', 'Average'), ('poor', 'Poor'),
                                         ('vpoor', 'Very poor')],
                                validators=[RequiredIf("tech", ["ok"])])
    en_txt = "Style"
    style = wtff.RadioField(en_txt,
                                    choices=[('excellent', 'Excellent'),
                                             ('good' ,'Good'),
                                             ('ave', 'Average'),
                                             ('poor', 'Poor'),
                                             ('vpoor', 'Very poor')],
                                    validators=[RequiredIf("tech", ["ok"])])
    en_txt = "Meaning"
    meaning = wtff.RadioField(en_txt,
                                    choices=[('excellent', 'Excellent'),
                                             ('good' ,'Good'),
                                             ('ave', 'Average'),
                                             ('poor', 'Poor'),
                                             ('vpoor', 'Very poor')],
                                    validators=[RequiredIf("tech", ["ok"])])
    en_txt = "Word choice"
    wordchoice = wtff.RadioField(en_txt,
                                    choices=[('excellent', 'Excellent'),
                                             ('good' ,'Good'),
                                             ('ave', 'Average'),
                                             ('poor', 'Poor'),
                                             ('vpoor', 'Very poor')],
                                    validators=[RequiredIf("tech", ["ok"])])
    en_txt = "Grammar"
    grammaticality = wtff.RadioField(en_txt,
                                    choices=[('excellent', 'Excellent'),
                                             ('good' ,'Good'),
                                             ('ave', 'Average'),
                                             ('poor', 'Poor'),
                                             ('vpoor', 'Very poor')],
                                    validators=[RequiredIf("tech", ["ok"])])
    en_txt = 'Specific comments on the chat interface'
    fr_txt = 'Commentaires spécifiques sur l\'interface de chat'
    interface = wtff.TextAreaField(en_txt, validators=[wtfv.Optional(),
                valid_input_text, MyLength3000])
    en_txt = 'Specific comments on the overall quality of the dialogue'
    fr_txt = 'Commentaires spécifiques sur la qualité générale du dialogue'
    verbatim_quality = wtff.TextAreaField({"english": en_txt, "french": fr_txt},
                        validators=[wtfv.Optional(),valid_input_text, MyLength3000])
    particular_problems = wtff.TextAreaField("particular_problems",
                        validators=[wtfv.Optional(), valid_input_text, MyLength3000])

    would_use = wtff.BooleanField('I would use such an application to communicate with people who speak another language.', validators=[])

    login = wtff.SubmitField('Ok')
