from flask import Blueprint
#from users import Login_container
import os

main = Blueprint('main', __name__)
main.config = {}

from . import routes, events
