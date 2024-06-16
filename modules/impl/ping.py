from modules.module import Module
from utils.vk_util import send_with_limit


class Ping(Module):

    def __init__(self):
        super().__init__(
            name="Ping",
            commands=["ping", "пинг"],
            subcommands=[],
            flags=[],
            access=0,
            super_access=5,
            description="Включен ли бот",
            always_on=True
        )

    @staticmethod
    def calculate_vk_ping():
        ...

    def on_message(self, event, who_called):
        # ping, uptime = self.calculateVkPing()
        return send_with_limit(
            user_id=event.user_id,
            random_id=0,
            peer_id=event.peer_id,
            reply_to=event.message_id,
            message=f"На месте"
            # message = f"Понг\nЗадержка VkAPI: {format(ping, '.2f')}. UPTIME: {format(uptime, '.2f')}"
        )
