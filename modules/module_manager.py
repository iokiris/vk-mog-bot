from modules.impl import voice_sender, ping, db, quote
from modules.module import Module
from vk_api.longpoll import VkEventType, Event
from utils.vk_util import send_with_limit, vk_timer
from utils.data import users_db


class ModuleManager:

    WHITELIST = []
    ADMIN_MODE = False

    def __init__(self, prefix: str = "."):
        self.modules: set[Module] = set()
        self.prefix: str = prefix

    def add(self, module):
        self.modules.add(module)

    def parse_command(self, text):
        args = text.split(" ")
        for m in self.modules:
            if args[0] in m.commands:
                return m
        return None

    def event_handler(self, event: Event):
        if event.type == VkEventType.MESSAGE_NEW:
            if event.text.startswith(self.prefix):

                if not vk_timer.should_reply(event.user_id):
                    return
                module = self.parse_command(event.text.lower()[len(self.prefix):])
                who_called = users_db.get_user(event.user_id)
                if who_called:
                    if who_called.access > 0:
                        if self.ADMIN_MODE:
                            if who_called.uid not in self.WHITELIST:
                                return send_with_limit(
                                    user_id=event.user_id,
                                    random_id=0,
                                    peer_id=event.peer_id,
                                    reply_to=event.message_id,
                                    message="Технические работы",
                                )
                        if event.text == self.prefix + 'help':
                            wrapped_info = f"🔧 Использование: \n {self.prefix}команда <действие> <аргументы> <флаги> \n"
                            wrapped_info += f"\nСписок команд для вашего доступа ({who_called.access}):"
                            for m in self.modules:
                                if m.access > who_called.access:
                                    continue
                                wrapped_info += f"\n{', '.join(m.commands)} ➖ {m.description}\n"
                                if len(m.subcommands) > 0:
                                    wrapped_info += "🛠Действия:\n"
                                    for sub in range(len(m.subcommands)):
                                        subcommand, description = m.subcommands[sub]
                                        if sub == len(m.subcommands) - 1:
                                            pre = "ㅤ└"

                                        else:
                                            pre = "ㅤ├"
                                        wrapped_info += f"{pre} {subcommand} ({description})\n"
                                if len(m.flags) > 0:
                                    wrapped_info += "ㅤ🚩Флаги:\n"
                                    for fl in range(len(m.flags)):
                                        flag, description = m.flags[fl]
                                        if fl == len(m.flags) - 1:
                                            pre = "ㅤㅤ└"
                                        else:
                                            pre = "ㅤㅤ├"
                                        wrapped_info += f"{pre} {flag} ({description})\n"
                            return send_with_limit(
                                user_id=event.user_id,
                                random_id=0,
                                peer_id=event.peer_id,
                                reply_to=event.message_id,
                                message=wrapped_info,
                            )
                        elif module:
                            if who_called.access >= module.access:
                                if module.active:
                                    module.on_message(event, who_called)
                            else:
                                return send_with_limit(
                                    user_id=event.user_id,
                                    random_id=0,
                                    peer_id=event.peer_id,
                                    reply_to=event.message_id,
                                    message=f"Недостаточно прав. {who_called.access} < {module.access}"
                                )
                    else:
                        print(event.user_id, "in the blacklist... Event has been ignored")

    def setup(self):
        self.add(voice_sender.VoiceSender())
        self.add(ping.Ping())
        self.add(db.Data())
        self.add(quote.Quote())
