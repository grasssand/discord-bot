import os
from io import BytesIO
from pathlib import Path
from typing import Tuple

import aiohttp
import genshinstats as gs
from dotenv import load_dotenv
from genshinstats.utils import is_chinese
from PIL import Image, ImageDraw, ImageFont

load_dotenv(Path(__file__).resolve().parent.parent / '.env', encoding='utf8')

MIHOYO_COOKIE_LTUID = os.getenv('MIHOYO_COOKIE_LTUID', '100000001')
MIHOYO_COOKIE_LTOKEN = os.getenv('MIHOYO_COOKIE_LTOKEN', '')
HOYOLAB_COOKIE_LTUID = os.getenv('HOYOLAB_COOKIE_LTUID', '100000001')
HOYOLAB_COOKIE_LTOKEN = os.getenv('HOYOLAB_COOKIE_LTOKEN', '')

SERVER_NAME = {
    '1': '天空岛',
    '5': '世界树',
    '6': '美服',
    '7': '欧服',
    '8': '亚服',
    '9': '港澳台服',
}


def set_font(size: int = 20):
    return ImageFont.truetype('./static/fonts/font.ttf', size=size)


def concat_img(img1, img2):
    new_img = Image.new('RGB', (img1.width, img1.height + img2.height))
    new_img.paste(img1, (0, 0))
    new_img.paste(img2, (0, img1.height))
    return new_img


async def check_character_img(character: dict) -> Path:
    img_path = Path(f"./static/chars/{character['id']}.png")
    if not img_path.is_file():
        async with aiohttp.ClientSession() as session:
            async with session.get(character['image']) as resp:
                with open(img_path, 'wb') as f:
                    while True:
                        chunk = await resp.content.read(10)
                        if not chunk:
                            break
                        f.write(chunk)
    return img_path


async def draw_user_img(uid: int, user_stats: dict):
    server = SERVER_NAME.get(str(uid)[0], '')
    img = Image.open('./static/images/info-new-upper.png').convert("RGBA")
    text_draw = ImageDraw.Draw(img)
    text_draw.text((280, 120), f'UID {uid}', '#263238', set_font(34))
    text_draw.text((400, 170), server, '#424242', set_font(30))

    # stats
    stats = user_stats['stats']
    text_draw.text((280, 292), f"{stats['active_day_number']}", '#263238', set_font(32))
    text_draw.text(
        (280, 346), f"{stats['achievement_number']}", '#263238', set_font(32)
    )
    text_draw.text((280, 400), f"{stats['avatar_number']}", '#263238', set_font(32))
    text_draw.text((280, 454), f"{stats['spiral_abyss']}", '#263238', set_font(32))
    text_draw.text(
        (620, 292), f"{stats['common_chest_number']}", '#263238', set_font(32)
    )
    text_draw.text(
        (620, 346), f"{stats['exquisite_chest_number']}", '#263238', set_font(32)
    )
    text_draw.text(
        (620, 400), f"{stats['precious_chest_number']}", '#263238', set_font(32)
    )
    text_draw.text(
        (620, 454), f"{stats['luxurious_chest_number']}", '#263238', set_font(32)
    )
    text_draw.text((960, 292), f"{stats['anemoculus_number']}", '#263238', set_font(32))
    text_draw.text((960, 346), f"{stats['geoculus_number']}", '#263238', set_font(32))
    text_draw.text((960, 400), f"--", '#263238', set_font(32))

    # home
    homes = ['hole', 'mountain', 'island']
    y = 110
    layer = Image.new('L', (213, 213))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle((0, 0, 213, 213), fill=255, radius=30)
    for home in homes:
        with Image.open(f'./static/images/{home}.png') as f:
            layer.paste(f, (0, 0), layer)
            img.paste(f, (1130, y), layer)
        y += 230

    # world_explorations
    world_explorations = user_stats['world_explorations']
    text_draw.text(
        (120, 710),
        f"{world_explorations[1]['exploration_percentage'] / 10}%",
        '#fff',
        set_font(28),
    )
    text_draw.text(
        (260, 710),
        f"Lv.{world_explorations[1]['level']}",
        '#fff',
        set_font(28),
    )
    text_draw.text(
        (460, 710),
        f"{world_explorations[2]['exploration_percentage'] / 10}%",
        '#fff',
        set_font(28),
    )
    text_draw.text(
        (600, 710),
        f"Lv.{world_explorations[2]['level']}",
        '#fff',
        set_font(28),
    )
    text_draw.text(
        (800, 710),
        f"{world_explorations[0]['exploration_percentage'] / 10}%",
        '#fff',
        set_font(28),
    )
    text_draw.text(
        (940, 710),
        f"Lv.{world_explorations[0]['level']}",
        '#fff',
        set_font(28),
    )

    # avatars
    box_x, box_y = 110, 10
    middle_img = None
    for i, character in enumerate(user_stats['avatars'], 1):
        if middle_img is None:
            middle_img = Image.open('./static/images/card-new-middle.png')

        char_img_path = await check_character_img(character)

        if character['name'] == 'Traveler':
            traveler = (
                Image.open(char_img_path)
                .convert("RGBA")
                .resize((180, 180), Image.BILINEAR)
            )
            img.paste(traveler, (90, 60), traveler)

        char_element = Image.open('./static/images/element.png').convert("RGBA")
        char_img = (
            Image.open(char_img_path).convert("RGBA").resize((150, 150), Image.BILINEAR)
        )
        char_element.paste(char_img, (9, 9), char_img)
        char_txt = ImageDraw.Draw(char_element)
        char_txt.text(
            (5, 2),
            f"C{character['actived_constellation_num']}",
            '#9575cd',
            set_font(22),
        )
        # w, h = char_txt.textsize(character['name'], set_font(20))
        # char_txt.text(
        #     ((159 - w) / 2, (150 - h)),
        #     character['name'],
        #     '#fff',
        #     set_font(20),
        # )
        char_txt.text(
            (50, 170),
            f"Lv.{character['level']}",
            '#64dd17',
            set_font(22),
        )
        char_txt.text(
            (50, 200),
            f"^_^{character['fetter']}",
            '#ff80ab',
            set_font(22),
        )
        middle_img.paste(char_element, (box_x, box_y), char_element)
        box_x += 180
        if (i % 7 == 0) or (i == stats['avatar_number']):
            img = concat_img(img, middle_img)
            middle_img.close()
            middle_img = None
            box_x = 110

    bottom_img = Image.open('./static/images/card-new-bottom.png')
    img = concat_img(img, bottom_img)

    file = BytesIO()
    img.save(file, format='png')
    img.close()
    file.seek(0)

    return file


async def get_user_stats(uid: int) -> dict:
    server = gs.recognize_server(uid)
    cn = is_chinese(uid)
    gs.set_cookie(
        ltuid=MIHOYO_COOKIE_LTUID if cn else HOYOLAB_COOKIE_LTUID,
        ltoken=MIHOYO_COOKIE_LTOKEN if cn else HOYOLAB_COOKIE_LTOKEN,
    )
    data = await gs.asyncify(
        gs.fetch_endpoint,
        "game_record/genshin/api/index",
        chinese=cn,
        params=dict(server=server, role_id=uid),
    )

    return data


async def get_user(uid: int) -> Tuple[str, str, BytesIO]:
    msg = ''
    filename = f'{uid}.png'
    file = BytesIO()
    try:
        user_stats = await get_user_stats(uid)
        file = await draw_user_img(uid, user_stats)
    except gs.errors.AccountNotFound:
        msg = '查无此用户。'
    except gs.errors.DataNotPublic:
        msg = '该用户隐藏了自己的秘密。'
    except Exception as e:
        msg = '查询出错'

    return msg, filename, file
