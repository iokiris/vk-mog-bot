from modules.module_manager import ModuleManager
from utils.vk_util import longpoll

manage_instance = ModuleManager()
manage_instance.setup()  # инициализация всех модулей

while True:
    try:
        for event in longpoll.listen():
            manage_instance.event_handler(event)
    except TypeError as e:
        ... # longpoll иногда просто так возвращает type-error который нужно игнорировать

    except Exception as ex:
        print(ex)
