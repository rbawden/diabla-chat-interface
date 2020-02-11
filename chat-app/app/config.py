# folder paths to store user and dialogue logs
dialogue_dir='/Users/rbawden/Sites/diabla/chat-app/logs/dialogues/'
user_dir='/Users/rbawden/Sites/diabla/chat-app/logs/users/'
tmodel_dir='/Users/rbawden/Sites/diabla/chat-app/logs/models/'
past_models='/Users/rbawden/Sites/diabla/chat-app/logs/models/past_models.json'

# models available
en2fr=tmodel_dir + '/en2fr'
fr2en=tmodel_dir + '/fr2en'
en2fr_2to2=tmodel_dir + '/en2fr-2to2'
fr2en_2to2=tmodel_dir + '/fr2en-2to2'

# tools for translation
preproc_dir='/opt/pre_and_postproc'
vars_en2fr=preproc_dir + '/' + 'en-fr.vars'
vars_fr2en=preproc_dir + '/' + 'fr-en.vars'
vars_en2fr_2to2=preproc_dir + '/' + 'en-fr.vars'
vars_fr2en_2to2=preproc_dir + '/' + 'fr-en.vars'

# models to choose from
tmodels = {"baseline": {"en2fr": en2fr, "fr2en": fr2en, "en2fr_port": 8080,
                         "fr2en_port": 8081, "concat_src": False,
                       "en2fr_vars": vars_en2fr, "fr2en_vars": vars_fr2en},
           "2to2": {"en2fr": en2fr_2to2, "fr2en": fr2en_2to2, "en2fr_port": 8082,
                    "fr2en_port": 8083,"concat_src": True,
                   "en2fr_vars": vars_en2fr_2to2, "fr2en_vars": vars_fr2en_2to2}
          }

# encryption password location
encryption_pw='/Users/rbawden/diabla.pw'
