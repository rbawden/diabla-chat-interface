import random
from app import all_users, config, tmodels
import logging
import os
import json
import time

random.seed(time.time())

def choose_random_scenario():
    scenarios = [[("You are both lost in a forest.",
                   "Vous êtes tous les deux perdus dans une forêt"),
                   ("", ""), ("", "")],
                 [("You are chefs preparing a meal.",
                   "Vous êtes deux cuisiners/cuisinières en train de préparer un repas."),
                    ("You are the head chef and you are talking to your subordinate.",
                     "Vous êtes le ou la chef(fe) et vous discutez avec votre chef(fe) adjoint."),
                    ("You are the subordinate chef and you are talking to the head chef.",
                     "Vous êtes le ou la chef(fe) adjoint(e) et vous discutez avec le/la chef(fe).")],
                 [("You are in a classroom.", "Vous êtes dans une salle de classe."),
                    ("You are the teacher and you are talking to a student.",
                     "Vous êtes le ou la professeur(e) et vous discutez avec un(e) élève(e) ou étudiant(e)."),
                    ("You are the student and you are talking to your teacher.",
                     "Vous êtes un(e) élève(e) ou étudiant(e) et vous discutez avec votre professeur(e).")],
                 [("You are feeding the ducks by the pond.",
                   "Vous nourrissez les canards au bord d'un étang."), ("", ""), ("", "")],
                 [("You are both organising a party.", "Vous organisez une fête."),
                    ("It's your party.", "C'est votre anniversaire"),
                    ("It's their party.", "C'est l'anniversaire de la personne avec qui vous discutez.")],
                [("You are both stuck in a lift at work.", "Vous êtes tous les deux bloqué(e)s dans un ascenseur au travail."),
                 ("You are an employee and you are with your boss.",
                  "Vous êtes un(e) employé(e) et vous êtes avec votre patron(ne)"),
                  ("You are the boss and are with an employee.", "Vous êtes le ou la patron(ne) et vous êtes avec un(e) employé(e)")],
                [("You are in a retirement home.", "Vous êtes dans une maison de retraite."),
                   ("You are visiting and talking to an old friend.", "Vous rendez visite et discutez avec un(e) vieil(le) ami(e)."),
                   ("You are a resident and you are talking with an old friend who is visiting you.", "Vous êtes un résident(e). Vous discutez avec un vieil ami qui est venu vous rendre visite")],
                [("You are in a bar.", "Vous êtes dans un bar."),
                   ("You are the bartender and talking to a customer.", "Vous êtes barman/barmaid et vous parlez à un(e) client(e)."),
                   ("You are a customer and are talking to the bartender.", "Vous êtes un(e) client(e) et vous parlez au barman/à la barmaid.")],
                [("You are in an aeroplane.", "Vous êtes dans un avion."),
                   ("You are scared and are speaking to the person sitting next to you.", "Vous avez peur de l'avion et parlez à la personne à côté de vous."),
                   ("You are speaking to the person next to you, who is scared.", "Vous parlez à la personne à côté de vous, qui a peur de l'avion.")],
                [("You are at home in the evening.", "Vous êtes à la maison le soir."),
                 ("You are telling your spouse about the awful day you had.",
                  "Vous racontez à votre partenaire la journée difficile que vous venez de passer."),
                  ("You are listening to your spouse telling you about the awful day they had.",
                   "Vous écoutez votre partenaire qui vous raconte la journée difficile qu'il/elle vient de passer.")],
                [("You are in a psychiatrist's consulting room.", "Vous êtes dans le cabinet d'un psychiatre."),
                 ("You are the psychiatrist and are with your patient.", "Vous êtes le psychiatre et parlez avec l'un(e) de vos patients"),
                 ("You are a patient and you are talking to your psychiatrist", "Vous êtes le ou la patient(e) et parlez avec votre psychiatre.")],
                [("You are on holiday by the pool.", "Vous êtes en vacances à côté de la piscine."),
                 ("You are trying to relax and the other person wants to do something else.", "Vous essayez de vous reposer et l'autre personne veut faire autre chose."),
                 ("You want to do something else and the other person is trying to relax", "Vous voulez faire autre chose et l'autre personne essaie de se reposer.")]
                 ]

    '''try:
        with open("/home/bawden/scenario_idx", "r") as fp:
            rand_idx = int(fp.read().strip())
            if rand_idx == len(scenarios) - 1:
                new_idx = 0
            elif rand_idx < 0:
                new_idx = random.choice(range(len(scenarios)))
            else:
                new_idx = rand_idx + 1
    except Exception:
        new_idx = random.choice(range(len(scenarios)))

    # write new number to file
    with open("/home/bawden/scenario_idx", "w") as fp:
        fp.write(str(new_idx))'''

    # choose the least used scenario
    if True:
        with open("/home/bawden/nb_scenarios.json", "r") as fp:
            scenario_nums = json.load(fp)
            new_idx, model = get_least_used(scenario_nums)

        # dump back to file
        scenario_nums[new_idx][model] += 1
        with open("/home/bawden/nb_scenarios.json", "w") as fp:
            json.dump(scenario_nums, fp, indent=3)


    #except Exception:
    #    new_idx = random.choice(range(len(scenarios)))
    #    model = None

    return scenarios[int(new_idx)], model

def get_least_used(scenarios):
    minimum, min_model, min_scenario = None, None, None
    for scenario in scenarios:
        for model in scenarios[scenario]:
            num = scenarios[scenario][model]
            #logging.info((scenario, model, num))
            if minimum is None or num < minimum:
                minimum = num
                min_model = model
                min_scenario = scenario

    #logging.info("\n\n\n\n" + str((min_scenario, min_model, minimum))+"\n\n\n\n")
    return min_scenario, min_model

def ratio_min_max(user, lambda_v = 0.00001):
    user_models = user.past_models
    for model in config.tmodels:
        if model not in user_models:
            user_models[model] = 0
    sorted_user_counts = sorted(user_models.items(), key=lambda x: x[1])
    minimum = sorted_user_counts[0]
    minimum_value = minimum[1] + lambda_v
    maximum = sorted_user_counts[-1][1] + lambda_v
    ratio = minimum_value/float(maximum)
    return minimum, ratio

def write_model_file():
    with open(config.past_models, "w") as fp:
        json.dump(tmodels, fp, indent=2)

def choose_tmodel(user1, user2):

    # for each model available, choose the one which most needs evaluations
    # given the two users
    minimum_models = [None, None]
    ratios = [0, 0]
    for i, user in enumerate([user1, user2]):
        minimum, ratio = ratio_min_max(user)
        ratios[i] = ratio
        minimum_models[i] = minimum

    os.sys.stderr.write("\n\n" + str(minimum_models) + " "+str(ratios)+ "\n")

    # if the same, take the least used model overall
    if ratios[0] == ratios[1]:
        chosen_model = sorted(tmodels.items(), key = lambda x: x[1])[0][0]
    elif ratios[0] < ratios[1]:
        chosen_model = minimum_models[0][0]
    else:
        chosen_model = minimum_models[1][0]

    os.sys.stderr.write("\n\n" + str(chosen_model) + "\n\n")

    # dump model file
    tmodels[chosen_model] += 1
    write_model_file()
    return chosen_model
