from vk_api.longpoll import Event
from classtypes import User


class Module:

    def __init__(self, name: str, commands: list[str], subcommands: list[tuple[str, str]], flags: list[tuple[str, str]],
                 access: int, super_access: int, description: str, always_on: bool):
        self.__name = name
        self.__commands = commands
        self.__subcommands = subcommands
        self.__flags = flags
        self.__access = access
        self.__description = description
        self.__active = always_on
        self.__super_access = super_access

        if self.__active:
            self.on_enable()

    @property
    def name(self):
        return self.__name

    @property
    def commands(self):
        return self.__commands

    @property
    def subcommands(self):
        return self.__subcommands

    @property
    def flags(self):
        return self.__flags

    @property
    def description(self):
        return self.__description

    @property
    def active(self):
        return self.__active

    @property
    def access(self):
        return self.__access

    @property
    def super_access(self):
        return self.__super_access

    def start(self):
        self.__active = True

    def stop(self):
        self.__active = False

    def on_enable(self):
        self.info("enabled")
        ...

    def on_disable(self):
        self.info("disabled")
        ...

    def on_event(self, event: Event):
        ...

    def on_message(self, event: Event, who_called: User):
        ...

    def on_request_limit(self, event: Event):
        ...

    def warn(self, content: any):
        print(f"[{self.__name}] | warn | {content}")

    def info(self, content: any):
        print(f"[{self.__name}] | info | {content}")