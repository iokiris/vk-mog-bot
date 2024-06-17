
import vk_api
import time
import re
from typing import Union, Dict, List
from vk_api.longpoll import VkLongPoll

from settings import config


vk_session = vk_api.VkApi(token=config.TOKEN, api_version='5.102')

longpoll: VkLongPoll = VkLongPoll(vk_session, )
vk = vk_session.get_api()

self_user = vk.users.get()[0]


class Timer:
    def __init__(self, req_limit: int = 3, time_limit: int = 60):
        self.recent_time: float = 0
        self.per_time: Dict[int, List[Union[int, float]]] = {}  # {user_id: [req_count, last_time]}
        self.no_delay_persons: List[int] = []
        self.req_limit: int = req_limit
        self.time_limit: int = time_limit

    @staticmethod
    def get_time() -> float:
        return time.time()

    def time_difference(self) -> float:
        return self.get_time() - self.recent_time

    def available_time(self, user_id: int) -> int:
        return int((self.per_time.setdefault(user_id, [0, 0])[1] + self.time_limit) - time.time())

    def reset(self) -> None:
        self.recent_time = self.get_time()

    def get_req_count(self, user_id: int) -> int:
        return self.per_time.get(user_id, [0, 0])[0]

    def time_exceeded(self, user_id: int) -> bool:
        if user_id in self.per_time:
            req_count, last_time = self.per_time[user_id]
            if req_count >= self.req_limit and (time.time() - last_time <= self.time_limit):
                return True
            if time.time() - last_time > self.time_limit:
                self.per_time[user_id] = [0, time.time()]
        return False

    def update_requests(self, user_id: int) -> bool:
        if user_id not in self.no_delay_persons:
            req_count, _ = self.per_time.get(user_id, [0, time.time()])
            self.per_time[user_id] = [req_count + 1, time.time()]
            return req_count + 1 >= self.req_limit
        return False

    def should_reply(self, user_id: int) -> bool:
        return not self.time_exceeded(user_id)


vk_timer = Timer(2, 30)


def get_token() -> str:
    return config.TOKEN


def parse_user(text: str, fields: str) -> Union[dict, None]:
    id_pattern = re.compile(r'\[id(\d+)\|.*\]')
    short_name_pattern = re.compile(r'https://vk\.com/(\w+)')
    id_match = id_pattern.match(text)
    try:
        if id_match:
            return vk.users.get(user_ids=int(id_match.group(1)), fields=fields)[0]

        short_name_match = short_name_pattern.match(text)
        if short_name_match:
            return vk.users.get(user_ids=short_name_match.group(1), fields=fields)[0]
    except vk_api.exceptions.ApiError:
        return None
    return None


def send_with_limit(user_id: int, **kwargs) -> None:
    if vk_timer.update_requests(user_id):
        if 'message' in kwargs:
            kwargs['message'] += (
                f'\n\n⏳ Достигнут лимит общих запросов. Я снова буду отвечать тебе через {vk_timer.available_time(user_id)} сек.'
            )
    vk.messages.send(**kwargs)
