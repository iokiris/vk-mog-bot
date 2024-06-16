from modules.module import Module
from utils.vk_util import vk_timer, send_with_limit, vk, parse_user
from utils.data import users_db
from classtypes import User


class Data(Module):

    def __init__(self):
        super().__init__(
            name="database",
            commands=['db'],
            subcommands=[
                ('cfgreset', 'сброс всех конфигов'), ('role', 'выдать доступ'),
                ('kick', 'удалить из бд'), ('blacklist', 'добавить в ЧС')
            ],
            flags=[],
            access=5,
            super_access=999,
            description='управление базой',
            always_on=True
        )

    def on_message(self, event, who_called):
        args: str = event.text.split(" ")[1:]
        c = len(args)
        if event.user_id:
            if vk_timer.should_reply(event.user_id):
                out_message = "Действие не найдено или произошла ошибка"
                if c < 2:
                    if args[0] == 'cfgreset':
                        users_db.reset_configs()
                        out_message = "Все конфиги сброшены"
                else:
                    user: object = parse_user(
                        text=args[1],
                        fields="can_write_private_message, blacklisted"
                    )
                    if user:
                        if args[0] == 'role':
                            if c >= 3:
                                if args[2].isdigit():
                                    users_db.update_access(user['id'], int(args[2]))
                                    out_message = f"[{user['id']}]: Новый уровень доступа: {users_db.get_user(user['id']).access}"
                        elif args[0] == 'kick':
                            if c >= 2:
                                users_db.remove_user(user['id'])
                                out_message = f"{user['id']} удален из БД"
                        elif args[0] == 'blacklist':
                            if c >= 2:
                                users_db.update_access(user['id'], -1)
                                out_message = f"{user['id']} добавлен в ЧС."
                return vk.messages.send(
                    random_id=0,
                    peer_id=event.peer_id,
                    reply_to=event.message_id,
                    message=out_message,
                )