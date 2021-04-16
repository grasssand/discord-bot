import os
from io import BytesIO
from pathlib import Path
from typing import Tuple

import genshinstats as gs
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv(Path(__file__).resolve().parent.parent / '.env', encoding='utf8')

MIHOYO_COOKIE_UID = os.getenv('MIHOYO_COOKIE_UID', '100000001')
MIHOYO_COOKIE_TOKEN = os.getenv('MIHOYO_COOKIE_TOKEN', '')


def get_user_info(uid: int) -> Tuple[dict, list]:
    gs.set_cookie(account_id=int(MIHOYO_COOKIE_UID), cookie_token=MIHOYO_COOKIE_TOKEN)
    user_info = gs.get_user_info(uid, raw=True)
    characters = gs.get_all_characters(uid, lang='zh-cn', raw=True)
    return user_info, characters


def set_font(size: int = 20):
    return ImageFont.truetype('./static/fonts/font.ttf', size=size)


def concat(img1, img2):
    new_img = Image.new('RGB', (img1.width, img1.height + img2.height))
    new_img.paste(img1, (0, 0))
    new_img.paste(img2, (0, img1.height))
    return new_img


def create_img(uid: str, user_info: dict, characters: list) -> BytesIO:
    if uid[0] == '1':
        server_name = '天空岛'
    elif uid[0] == '5':
        server_name = '世界树'
    elif uid[0] == '6':
        server_name = '美服'
    elif uid[0] == '7':
        server_name = '欧服'
    elif uid[0] == '8':
        server_name = '亚服'
    elif uid[0] == '9':
        server_name = '港澳台服'
    else:
        server_name = ''

    img = Image.open('./static/images/top.png').convert("RGBA")
    text_draw = ImageDraw.Draw(img)
    text_draw.text((250, 120), f'UID {uid}', '#263238', set_font(32))
    text_draw.text((350, 170), server_name, '#424242', set_font(28))

    # stats
    stats = user_info['stats']
    text_draw.text((280, 290), f"{stats['active_day_number']}", '#263238', set_font(32))
    text_draw.text(
        (280, 342), f"{stats['achievement_number']}", '#263238', set_font(32)
    )
    text_draw.text((280, 394), f"{stats['anemoculus_number']}", '#263238', set_font(32))
    text_draw.text((280, 446), f"{stats['geoculus_number']}", '#263238', set_font(32))
    text_draw.text((280, 498), f"{stats['avatar_number']}", '#263238', set_font(32))
    text_draw.text(
        (740, 290), f"{stats['common_chest_number']}", '#263238', set_font(32)
    )
    text_draw.text(
        (740, 342), f"{stats['exquisite_chest_number']}", '#263238', set_font(32)
    )
    text_draw.text(
        (740, 394), f"{stats['precious_chest_number']}", '#263238', set_font(32)
    )
    text_draw.text(
        (740, 446), f"{stats['luxurious_chest_number']}", '#263238', set_font(32)
    )
    text_draw.text((740, 498), f"{stats['spiral_abyss']}", '#263238', set_font(32))

    # world_explorations
    world_explorations = user_info['world_explorations']
    text_draw.text(
        (100, 800),
        f"{world_explorations[0]['exploration_percentage'] / 10}%",
        '#fff',
        set_font(28),
    )
    text_draw.text(
        (220, 800),
        f"Lv.{world_explorations[0]['level']}",
        '#fff',
        set_font(28),
    )
    text_draw.text(
        (360, 800),
        f"{world_explorations[1]['exploration_percentage'] / 10}%",
        '#fff',
        set_font(28),
    )
    text_draw.text(
        (495, 800),
        f"Lv.{world_explorations[1]['level']}",
        '#fff',
        set_font(28),
    )
    text_draw.text(
        (640, 800),
        f"{world_explorations[2]['exploration_percentage'] / 10}%",
        '#fff',
        set_font(28),
    )
    text_draw.text(
        (775, 800),
        f"Lv.{world_explorations[2]['level']}",
        '#fff',
        set_font(28),
    )

    # avatars
    box_x, box_y = 80, 10
    middle_img = None
    for i, character in enumerate(characters, 1):
        if middle_img is None:
            middle_img = Image.open('./static/images/middle.png').resize(
                (934, 160), Image.BILINEAR
            )

        if character['name'] == '旅行者':
            traveler = (
                Image.open(f"./static/chars/{character['id']}.png")
                .convert("RGBA")
                .resize((180, 180), Image.BILINEAR)
            )
            img.paste(traveler, (70, 50), traveler)

        char_element = (
            Image.open('./static/images/element.png')
            .convert("RGBA")
            .resize((100, 150), Image.BILINEAR)
        )
        char_img = (
            Image.open(f"./static/chars/{character['id']}.png")
            .convert("RGBA")
            .resize((100, 100), Image.BILINEAR)
        )
        char_element.paste(char_img, (0, 0), char_img)
        char_txt = ImageDraw.Draw(char_element)
        constellations = len(
            list(filter(lambda x: x['is_actived'], character['constellations']))
        )
        char_txt.text(
            (5, 2),
            f"C{constellations}",
            '#9575cd',
            set_font(14),
        )
        w, h = char_txt.textsize(character['name'], set_font(14))
        char_txt.text(
            ((100 - w) / 2, 85),
            character['name'],
            '#fff',
            set_font(14),
        )
        char_txt.text(
            (28, 105),
            f"Lv.{character['level']}",
            '#64dd17',
            set_font(14),
        )
        char_txt.text(
            (28, 125),
            f"^_^{character['fetter']}",
            '#ff80ab',
            set_font(14),
        )
        middle_img.paste(char_element, (box_x, box_y), char_element)
        box_x += 110
        if (i % 7 == 0) or (i == len(user_info['avatars'])):
            img = concat(img, middle_img)
            middle_img.close()
            middle_img = None
            box_x = 80

    bottom_img = Image.open('./static/images/bottom.png')
    img = concat(img, bottom_img)

    file = BytesIO()
    img.save(file, format='png')
    img.close()

    return file


def get_user(uid: int) -> Tuple[str, str, BytesIO]:
    msg = ''
    filename = f'{uid}.png'
    file = BytesIO()
    try:
        user_info, characters = get_user_info(uid)
        file = create_img(str(uid), user_info, characters)
    except gs.errors.DataNotPublic:
        msg = '该用户隐藏了自己的秘密。'
    except gs.errors.InvalidUID:
        msg = '查无此用户。'
    except Exception:
        msg = '查询出错'

    return msg, filename, file
