# DiaBLa chat interface

*Bilingual chat interface for dialogues mediated by machine translation (MT) systems.*

This interface is designed for the collection of bilingual dialogues between two speakers of different languages (in this version, this is for English and French). The dialogue is entirely mediated by two MT systems and each participant only sees the dialogue in their own language. The interfaces enables users to register an account, log in, choose who they want to talk to (in a meeting room) and dialogue according to a chosen fictional scenario. 

In addition, the users indicate in real-time any errors they perceive in the machine translated versions of their partner's utterances.

The interface can be adapted for new languages and new MT models and to collect additional data.

## Acknowledgments

This code has been adapted from https://github.com/miguelgrinberg/Flask-SocketIO-Chat.

If you use this adapted and augmented version, please cite the following paper:

```
@article{bawden_diabla2019,
    author = {Rachel Bawden and Sophie Rosset and Thomas Lavergne and Eric Bilinski},
    title = {DiaBLa: A Corpus of Bilingual Spontaneous Written Dialogues for Machine Translation},
    year = {2019},
    url = {http://arxiv.org/abs/1905.13354},
    journal = {CoRR}
}
```

The English-French parallel dialogue dataset collected using this interface can be found [here](https://github.com/rbawden/DiaBLa-dataset).

## Licence

The code is distributed under a LGPL-3.0 licence.


## Requirements

Code has been tested with python 3.4

`pip install -r requirements.txt`

`pip install git+https://github.com/mrhwick/schedule.git`


## Setup and configuration

To run the chat application, install the requirements, navigate to `chat-app/` and run:

`python chat.py`

By default, the chat application will be available on `http://localhost:5000` in a browser.

A certain number of options will have to be configured for the application to run on your machine (paths to models, scripts, languages and addresses). These can be found in the following files:

- `chat-app/app/settings.py` - contains the list of scenarios (and the text that will be displayed in both languages)
- `chat-app/app/config.py` - contains paths to MT models, tools for translation, folder paths to store logs of the registered users and completed dialogues.

To set up for new MT models:

- translation servers should be set up on different ports (one for English-to-French, one for French-to-English)
- the code is currently configured such that the translation servers can be queried using `localhost:PORT_NUMBER/translate` (see the `translate` function in `chat-app/app/main/events.py` 

## Example usage
