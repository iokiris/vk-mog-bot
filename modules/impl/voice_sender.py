from modules.module import Module
from utils.vk_util import vk, vk_timer, send_with_limit, parse_user, Timer, self_user
from vk_api.longpoll import Event
from threading import Thread
from utils.data import users_db
from typing import Union
import random
import time
import json


class VoiceSender(Module):

    MAX_VOICE_COUNT = 15

    def __init__(self):
        super().__init__(
            name="VoiceSender",
            commands=["vs", "гс"],
            subcommands=[
                ("add", "добавить пересланные гс"), ("stop", "остановить работу"), ("reset", "сбросить конфиг"),
                ("list", "список гс"), ("del", "удалить гс")
            ],
            flags=[
                ("-fwd", "переслать результат"), ("-shuffle", "перемешать гс"), ("-delay", "задержка x3")
            ],
            access=3,
            super_access=5,
            description="отправка гс из вашего конфига",
            always_on=True
        )

        self.default_limit = 15
        self.queue: set[int] = set()
        self.isBusy = False
        self.voices: set[str] = set()
        self.stopThreads = False
        self.lastThreadCaller: int = 0
        self.timer = Timer(1, 600)
        self.adminMode = False
        self.ignore_list = [self_user['id']]  # Те, кому нельзя отправлять сообщения

    def set_busy(self):
        self.isBusy = True

    def un_busy(self):
        self.stopThreads = False
        self.isBusy = False

    @staticmethod
    def get_voices(user_id: int) -> Union[list, None]:
        u = users_db.get_user(user_id)
        if u:
            return json.loads(u.voice_config)
        return None

    @staticmethod
    def audio_to_doc(audio: dict) -> Union[str, None]:
        if 'owner_id' in audio and 'id' in audio and 'access_key' in audio:
            return f"doc{audio['owner_id']}_{audio['id']}_{audio['access_key']}"
        return None

    @staticmethod
    def forward_messages(uid: int, message: str, event):
        messages = vk.messages.getHistory(peer_id=uid)
        ids = []
        if messages['count'] > 0:
            for i in messages['items']:
                ids.append(str(i['id']))
        return vk.messages.send(
            random_id=0,
            peer_id=event.user_id,
            message=message,
            forward_messages=",".join(ids)
        )

    def send_voicelist(self, event):
        voices = self.get_voices(event.user_id)
        msg = ""
        for i in range(len(voices)):
            msg += f"{i + 1}. {voices[i]['link']}\n"
        send_with_limit(
            user_id=event.user_id,
            random_id=0,
            peer_id=event.peer_id,
            reply_to=event.message_id,
            message=f"Список сохраненных ГС: \n{msg}"
        )

    def target_user(self, uid: int, event):
        self.lastThreadCaller = event.user_id
        voices = [item['att'] for item in self.get_voices(event.user_id)]
        should_shuffle = 'Нет'
        should_forward = 'Нет'
        k = 1
        if '-shuffle' in event.text.lower():
            should_shuffle = 'Да'
            random.shuffle(voices)
        if '-fwd' in event.text.lower():
            should_forward = 'Да'

        if "-delay" in event.text.lower():
            k = 3

        if len(voices) == 0:
            return vk.messages.send(
                random_id=0,
                peer_id=event.peer_id,
                reply_to=event.message_id,
                message="❗ Не найден конфиг. Добавь голосовые сообщения.",
            )
        self.timer.update_requests(event.user_id)
        send_with_limit(
            user_id=event.user_id,
            random_id=0,
            peer_id=event.peer_id,
            reply_to=event.message_id,
            message=f"🚀 Запущен. \nПеремешать гс: {should_shuffle}\nПереслать сообщения: {should_forward}\nЗадержка: x{k}",
        )
        self.isBusy = True
        counter = 0
        for voice in voices:
            try:
                if self.stopThreads:
                    self.un_busy()
                    if should_forward == 'Да':
                        return self.forward_messages(uid=uid,
                                                     message=f"⏸️ Работа завершена. Отправлено: {counter} / {len(voices)}",
                                                     event=event)
                    return vk.messages.send(
                        random_id=0,
                        peer_id=event.peer_id,
                        reply_to=event.message_id,
                        message=f"⏸️ Работа завершена. Отправлено: {counter} / {len(voices)}",
                    )

                vk.messages.send(
                    peer_id=uid,
                    attachment=voice,
                    random_id=0,
                )
                counter += 1

            except Exception as e:
                self.warn(f"stopThreads: {self.stopThreads}, Error: {e}")
                self.timer.update_requests(event.user_id)
                self.un_busy()
                if should_forward == 'Да':
                    return self.forward_messages(
                        uid=uid, message=f"❌ Произошла ошибка. Отправлено {counter} из {len(voices)}",
                        event=event
                    )
                return vk.messages.send(
                    peer_id=event.peer_id,
                    message=f"❌ Произошла ошибка. Отправлено {counter} из {len(voices)}",
                    reply_to=event.message_id,
                    random_id=0
                )
            elapse = random.uniform(15 * k, 36 * k)
            e = 0
            while not self.stopThreads and e < elapse:
                if e % 5 == 0:
                    try:
                        vk.messages.markAsRead(peer_id=uid)
                        vk.messages.setActivity(peer_id=uid, type='audiomessage')
                    except:
                        self.stopThreads = True
                time.sleep(0.5)
                e += 0.5
        self.timer.update_requests(event.user_id)
        self.un_busy()
        if should_forward == 'Да':
            return self.forward_messages(
                uid=uid, message=f"✅ Работа завершена. Отправлено {counter} из {len(voices)}", event=event
            )
        return vk.messages.send(
            peer_id=event.peer_id, random_id=0, reply_to=event.message_id,
            message=f"✅ Работа завершена. Отправлено {counter} из {len(voices)}"
        )

    def init_voice_list(self, event):
        response = vk.messages.getHistoryAttachments(
            peer_id=event.peer_id,
            count=200,
            media_type="audio_message"
        )
        if len(response['items']) == 0:
            msg = "📢 Голосовые сообщения не найдены."
        else:
            msg = f"Найдено {len(response['items'])} голосовых сообщений.\n"
            c = 0
            for item in response['items']:
                try:
                    audio = item['attachment']['audio_message']
                    self.voices.add(f'doc{audio["owner_id"]}_{audio["id"]}_{audio["access_key"]}')
                    c += 1
                except KeyError as e:
                    self.warn(e)
                    continue
            msg += f"➕ Добавлено: {c}. Всего: {len(self.voices)}"
        return vk.messages.send(
            random_id=0,
            peer_id=event.peer_id,
            reply_to=event.message_id,
            message=msg,
        )

    @staticmethod
    def get_audio_message(attachments):
        for attachment in attachments:
            if attachment['type'] == 'audio_message':
                return attachment['audio_message']
        return None

    def extract_audio_messages(self, messages):
        audio_messages = []
        for message in messages:
            if 'attachments' in message:
                audio = self.get_audio_message(message['attachments'])
                if audio:
                    audio_messages.append(audio)

            # рекурсия для обработки вложенных пересланных сообщений
            if 'reply_message' in message:

                audio_messages.extend(self.extract_audio_messages([message['reply_message']]))
            else:
                audio_messages.extend(self.extract_audio_messages(message.get('fwd_messages', [])))

        return audio_messages

    def contains_audio(self, voice_list: list[dict], voice: str) -> Union[dict, None]:
        spvoice = voice.split("_")
        for v in voice_list:
            spv = v['att'].split("_")
            if spv[0] == spvoice[0] and spv[1] == spvoice[1]:
                return v
        return None

    def fill_voices(self, user_id: int, voices: list, check_limit: bool):
        user_voices = self.get_voices(user_id)
        c = 0
        for voice in voices:
            if len(user_voices) >= self.default_limit and check_limit:
                break
            str_voice = self.audio_to_doc(voice)
            if str_voice:
                if not self.contains_audio(user_voices, str_voice):
                    user_voices.append({
                        "att": str_voice,
                        "link": vk.utils.getShortLink(url=voice['link_mp3'])['short_url']
                    })
                    time.sleep(1.0)
                    c += 1
        users_db.update_config(
            user_id,
            json.dumps(user_voices)
        )
        return c

    def remove_voice_from_number(self, event: Event, numbers: list[int], need_answer: bool):
        voices = self.get_voices(event.user_id)
        counter = 0
        for number in sorted(numbers, reverse=True):
            if number > len(voices) or number < 1:
                ...
            else:
                voices.remove(voices[number - 1])
                counter += 1
        users_db.update_config(event.user_id, json.dumps(voices))
        msg = "📢 Голосовые сообщения не найдены"
        if counter > 0:
            msg = f"➖ Удалено {counter} гс."
        return send_with_limit(
            user_id=event.user_id,
            random_id=0,
            peer_id=event.peer_id,
            reply_to=event.message_id,
            message=f"➖ Удалено {counter} гс.",
        )

    def remove_replied_voices(self, user_id: int, voices: list):
        user_voices = self.get_voices(user_id)
        c = 0
        for voice in voices:
            str_voice = self.audio_to_doc(voice)
            if str_voice:
                k = self.contains_audio(user_voices, str_voice)
                if k:
                    user_voices.remove(k)
                    c += 1
        if c > 0:
            users_db.update_config(
                user_id,
                json.dumps(user_voices)
            )
        return c

    def reset_voice(self, user_id: int):
        users_db.update_config(
            user_id,
            '[]'
        )

    def on_message(self, event, who_called):
        args = event.text.split(" ")[1:]

        if event.user_id:
            if vk_timer.should_reply(event.user_id):
                if len(args) == 0:
                    return send_with_limit(
                        user_id=event.user_id,
                        random_id=0,
                        peer_id=event.peer_id,
                        reply_to=event.message_id,
                        message="⚠️ Недостаточно аргументов.",
                    )

                if args[0] == 'init':
                    # return self.initVoiceList(event)
                    ...
                elif args[0] == 'list':
                    return self.send_voicelist(event)
                elif args[0] == 'add':
                    send_with_limit(
                        user_id=event.user_id,
                        random_id=0,
                        peer_id=event.peer_id,
                        reply_to=event.message_id,
                        message="🔎 Поиск голосовых сообщений",
                    )
                    caught_audio = []
                    if 'reply' in event.attachments:
                        replied = vk.messages.getByConversationMessageId(
                            peer_id=event.peer_id,
                            conversation_message_ids=json.loads(event.attachments['reply'])[
                                'conversation_message_id']
                        )
                        caught_audio = self.extract_audio_messages(replied['items'])
                    else:
                        m = vk.messages.getById(message_ids=event.message_id)
                        if len(m['items']) > 0:
                            caught_audio = self.extract_audio_messages(m['items'])
                    if len(caught_audio) > 0:
                        check_limit = True
                        if who_called.access >= self.super_access:
                            check_limit = False
                        msg = f"➕ Добавлено {self.fill_voices(event.user_id, caught_audio, check_limit)} гс."
                    else:
                        msg = "📢 Голосовые сообщения не найдены"
                    return send_with_limit(
                        user_id=event.user_id,
                        random_id=0,
                        peer_id=event.peer_id,
                        reply_to=event.message_id,
                        message=msg,
                    )
                elif args[0] == 'del':
                    caught_audio = []
                    if len(args) > 1:
                        if len(args) >= 3:
                            items = list(map(int, args[1:]))
                            return self.remove_voice_from_number(event, items, True)
                        elif args[1].isdigit() and len(args) < 3:
                            return self.remove_voice_from_number(event, [int(args[1])], True)
                        elif "-" in args[1]:
                            start, end = map(int, args[1].split("-"))
                            return self.remove_voice_from_number(event, list(range(min(start, end), max(start, end) + 1)), True)
                    elif 'reply' in event.attachments:
                        replied = vk.messages.getByConversationMessageId(
                            peer_id=event.peer_id,
                            conversation_message_ids=json.loads(event.attachments['reply'])[
                                'conversation_message_id']
                        )
                        caught_audio = self.extract_audio_messages(replied['items'])
                    else:
                        m = vk.messages.getById(message_ids=event.message_id)
                        if len(m['items']) > 0:
                            caught_audio = self.extract_audio_messages(m['items'])
                    if len(caught_audio) > 0:
                        msg = f"➖ Удалено {self.remove_replied_voices(event.user_id, caught_audio)} гс."
                    else:
                        msg = "📢 Голосовые сообщения не найдены"
                    return send_with_limit(
                        user_id=event.user_id,
                        random_id=0,
                        peer_id=event.peer_id,
                        reply_to=event.message_id,
                        message=msg,
                    )
                elif args[0] == 'reset':
                    self.reset_voice(event.user_id)
                    return send_with_limit(
                        user_id=event.user_id,
                        random_id=0,
                        peer_id=event.peer_id,
                        reply_to=event.message_id,
                        message="🔄 Конфиг сброшен",
                    )
                user: dict = parse_user(
                    text=args[0],
                    fields="can_write_private_message, blacklisted"
                )

                if user:
                    if self.isBusy:
                        return send_with_limit(
                            user_id=event.user_id,
                            random_id=0,
                            peer_id=event.peer_id,
                            reply_to=event.message_id,
                            message="В данный момент я занят. Попробуй позже.",
                        )
                    else:
                        if user['id'] in self.ignore_list:
                            return send_with_limit(
                                user_id=event.user_id,
                                random_id=0,
                                peer_id=event.peer_id,
                                reply_to=event.message_id,
                                message="Команда запрещена для этого человека.",
                            )
                        elif user['blacklisted']:
                            return send_with_limit(
                                user_id=event.user_id,
                                random_id=0,
                                peer_id=event.peer_id,
                                reply_to=event.message_id,
                                message="Этот человек добавил меня в чёрный список.",
                            )
                        elif not user['can_write_private_message']:
                            return send_with_limit(
                                user_id=event.user_id,
                                random_id=0,
                                peer_id=event.peer_id,
                                reply_to=event.message_id,
                                message="У этого человека закрыты личные сообщение для меня.",
                            )
                        else:
                            if self.timer.should_reply(event.user_id):
                                Thread(
                                    target=self.target_user,
                                    args=(user['id'], event)
                                ).start()

                            else:
                                return send_with_limit(
                                    user_id=event.user_id,
                                    random_id=0,
                                    peer_id=event.peer_id,
                                    reply_to=event.message_id,
                                    message=f"⏰ Это будет доступно тебе через {self.timer.available_time(event.user_id)} сек.",
                                )
            else:
                return self.info(f"Too much requests from {event.user_id}")

            if args[0].lower() == 'stop':
                if self.lastThreadCaller == event.user_id or who_called.access > self.super_access:
                    if not self.stopThreads and self.isBusy:
                        self.stopThreads = True
