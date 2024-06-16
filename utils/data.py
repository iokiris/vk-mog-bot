from os import path
from utils.db_controller import DataHandler

PATH = path.dirname(path.dirname(path.abspath(__file__)))

users_db = DataHandler(f"{PATH}/databases/users.db")


def init_users():
    users_db.add_tabble()
    print("[DATA]: users initialized")


def init_all():
    init_users()
    print("All db connected")


init_all()
