import sqlite3
from typing import Union

from classtypes import User


class DataHandler:

    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.cursor = self.db.cursor()

    def add_tabble(self):
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            userid       INT  PRIMARY KEY,
            access       INT,
            voice_config TEXT
        );
            """)

    def get_all_users(self) -> list[User]:
        users: list[User] = []
        self.cursor.execute(
            "SELECT * FROM users"
        )
        for u in self.cursor.fetchall():
            users.append(User(*u))
        return users

    # @cached(cache=TTLCache(maxsize=128, ttl=60))
    def get_user(self, user_id: int) -> Union[User, None]:

        query = f"SELECT * FROM users WHERE userid = {user_id};"
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        if result:
            return User(*result)
        return None

    def get_access(self, user_id: int) -> int:
        user = self.get_user(user_id)
        if user:
            return user.access
        return 0

    def update_user(self, user_obj: User):
        user = self.cursor.execute(
            f"SELECT 1 FROM users WHERE userid == {user_obj.uid}"
        ).fetchone()
        if not user:
            self.cursor.execute(
                "INSERT INTO users VALUES(?, ?, ?)",
                (user_obj.uid, user_obj.access, user_obj.voice_config)
            )
        else:
            self.cursor.execute(
                f"UPDATE users SET access = ?, voice_config = ? WHERE userid = ?",
                (user_obj.access, user_obj.voice_config)
            )
        self.db.commit()

    def update_access(self, user_id: int, lvl: int):
        user: User = self.get_user(user_id)
        if not user:
            return self.update_user(User(user_id=user_id, access=lvl, voice_config='[]'))
        self.cursor.execute(f"UPDATE users SET access = {lvl} WHERE userid = {user_id};")
        self.db.commit()

    def update_config(self, user_id: int, config: str):
        user: User = self.get_user(user_id)
        if user:
            self.cursor.execute("UPDATE users SET voice_config = ? WHERE userid = ?;", (config, user_id))
            self.db.commit()
        else:
            self.update_user(User(user_id=user_id, access=0, voice_config=config))

    def remove_user(self, uid):
        self.cursor.execute(
            "DELETE FROM users WHERE userid == ?",
            (uid,)
        )
        self.db.commit()

    def reset_configs(self):
        for user in self.get_all_users():
            self.update_config(user.uid, '[]')
