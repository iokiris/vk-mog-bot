import time
from io import BytesIO
from pathlib import Path
import json
import requests
import textwrap
from PIL import Image, ImageDraw, ImageFont
import concurrent.futures

from modules.module import Module
from settings import config
from utils.vk_util import vk, get_token

current_path = Path(__file__)
PARENT_PATH = current_path.parents[2]

regular_font = ImageFont.truetype(f"{PARENT_PATH}/static/fonts/Roboto-Regular.ttf", size=48)
italic_font = ImageFont.truetype(f'{PARENT_PATH}/static/fonts/Roboto-Italic.ttf', size=36)

try:
    background = Image.open(f'{PARENT_PATH}/static/media/quotes_bg.png')
except FileNotFoundError:
    background = Image.new('RGBA', (512, 512), (0, 0, 0, 255))


class Quote(Module):

    def __init__(self):
        super().__init__(
            name="Quote",
            commands=["цит", "quote"],
            subcommands=[],
            flags=[],
            access=2,
            super_access=5,
            description="делает цитату",
            always_on=True
        )

    @staticmethod
    def gen_quote(title: str, text: str, author: str, profile_img: Image.Image):
        if len(text) > 2048:
            return
        margin = 50
        offset = 300
        wrapped_text = textwrap.wrap(text, width=45)

        img = background.resize((1000, max(400, 300 + len(wrapped_text) * 45)))
        draw = ImageDraw.Draw(img)
        w, _ = draw.textbbox((0, 0), title, font=regular_font)[2:]
        draw.text(
            ((1000 - w) / 2, 25 + regular_font.size / 2),
            title,
            font=regular_font,
            fill="#ffffff"
        )
        img.paste(profile_img, (50, 120), profile_img)
        _, author_name_size_height = draw.textbbox((0, 0), author, font=regular_font)[2:]
        draw.text(
            (235, 120 + author_name_size_height),
            f'© {author}',
            font=regular_font,
            fill="#ffffff"
        )
        for line in wrapped_text:
            draw.text((margin, offset), line, font=italic_font, fill="#ffffff")
            offset += italic_font.getbbox(line)[3]

        fp = BytesIO()
        img.save(fp, format='PNG')
        fp.seek(0)

        return fp

    @staticmethod
    def prepare_mask(size, antialias=2):
        mask = Image.new('L', (size[0] * antialias, size[1] * antialias), 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + mask.size, fill=255)
        return mask.resize(size, Image.Resampling.LANCZOS)

    @staticmethod
    def crop(im, s):
        w, h = im.size
        k = w / s[0] - h / s[1]
        if k > 0:
            im = im.crop(((w - h) / 2, 0, (w + h) / 2, h))
        elif k < 0:
            im = im.crop((0, (h - w) / 2, w, (h + w) / 2))
        return im.resize(s, Image.Resampling.LANCZOS)

    def handle_message(self, event, who_called):
        start_time = time.time()
        size = (150, 150)
        uid, text = None, ""
        if 'reply' in event.attachments:
            replied = vk.messages.getByConversationMessageId(
                peer_id=event.peer_id,
                conversation_message_ids=json.loads(event.attachments['reply'])[
                    'conversation_message_id']
            )['items'][0]
            uid = replied['from_id']
            text = replied['text']

        else:
            m = vk.messages.getById(message_ids=event.message_id)['items']
            if len(m) > 0:
                replied = m[0]['fwd_messages']
                uid = replied[0]['from_id']
                for r in replied:
                    if r['from_id'] != uid:
                        return

                text = ". ".join(map(lambda d: d['text'], replied))
        if not uid or len(text) < 8:
            return
        user = vk.users.get(user_ids=uid, fields='photo_200')[0]
        photo = requests.get(user['photo_200'], stream=True).raw
        username = f"{user['first_name']} {user['last_name']}"
        im = Image.open(photo)
        im = self.crop(im, size)
        im.putalpha(self.prepare_mask(size, 4))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.gen_quote, config.QUOTE_TITLE_MESSAGE, f'{text}', username, im)
            quote_image = future.result()

        if quote_image is None:
            vk.messages.send(peer_id=event.peer_id, message="Ошибка при создании цитаты", random_id=0)
            return

        upload_struct = requests.post(
            requests.get('https://api.vk.com/method/{method}?{params}&access_token={token}&v=5.95'.format(
                method='photos.getMessagesUploadServer',
                params=f'peer_id={event.peer_id}',
                token=get_token())
            ).json()['response']['upload_url'], files={'file': ('photo.png', quote_image, 'image/png')}
        ).json()
        photo_save = requests.get('https://api.vk.com/method/{method}?{params}&access_token={token}&v=5.95'.format(
            method='photos.saveMessagesPhoto',
            params=f"server={upload_struct['server']}&photo={upload_struct['photo']}&hash={upload_struct['hash']}",
            token=get_token())
        ).json()['response'][0]
        vk.messages.send(
            peer_id=event.peer_id, message=f"Время обработки: {format(time.time() - start_time, '.2f')}с.",
            attachment=f"photo{photo_save['owner_id']}_{photo_save['id']}_{photo_save['access_key']}", random_id=0
        )

    def on_message(self, event, who_called):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(self.handle_message, event, who_called)
