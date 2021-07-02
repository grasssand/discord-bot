import json
import os
from datetime import datetime, timedelta
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import aiofiles
import aiohttp
import genshinstats as gs
from dotenv import load_dotenv
from genshinstats.utils import is_chinese
from PIL import Image, ImageDraw, ImageFont

from discord_bot.genshin_character_id import GENSHIN_CHARACTER_ID
from discord_bot.logger import logger

log = logger(__name__)

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

ELEMENT_COLORS = {
    'Anemo': '#3C8B6D',
    'Cryo': '#5C9DAB',
    'Dendro': '#789B34',
    'Electro': '#946FAE',
    'Geo': '#A39982',
    'Hydro': '#2A8AA9',
    'Pyro': '#B07451',
}

ELEMENT_BACKGROUND_COLORS = {
    'Anemo': '#C7DDD5',
    'Cryo': '#C0E7F2',
    'Dendro': '#B4E84E',
    'Electro': '#D0CCE1',
    'Geo': '#F0E1C0',
    'Hydro': '#C5D7E3',
    'Pyro': '#ECC5C3',
}


class SourceType(Enum):
    Avatar = 'avatars'
    Character = 'characters'
    Weapon = 'weapons'
    Artifact = 'artifacts'


def set_font(size: int = 20):
    return ImageFont.truetype('./static/fonts/font.ttf', size=size)


def concat_img(img1, img2):
    new_img = Image.new('RGB', (img1.width, img1.height + img2.height))
    new_img.paste(img1, (0, 0))
    new_img.paste(img2, (0, img1.height))
    return new_img


async def get_img_path(source: SourceType, id: int, url: Optional[str] = None) -> Path:
    img_path = Path(f"./static/genshin/{source.value}/{id}.png")
    if url and not img_path.is_file():
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                with open(img_path, 'wb') as f:
                    while True:
                        chunk = await resp.content.read(10)
                        if not chunk:
                            break
                        f.write(chunk)
    return img_path


async def draw_user_img(uid: int, user_stats: dict) -> BytesIO:
    server = SERVER_NAME.get(str(uid)[0], '')
    img = Image.open('./static/images/info-new-upper.png').convert('RGBA')
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
        with Image.open(f'./static/images/{home}.png').convert('RGBA') as f:
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
            middle_img = Image.open('./static/images/card-new-middle.png').convert(
                'RGBA'
            )

        char_img_path = await get_img_path(
            SourceType.Avatar, character['id'], character['image']
        )

        if character['name'] == 'Traveler':
            traveler = (
                Image.open(char_img_path)
                .resize((180, 180), Image.BILINEAR)
                .convert('RGBA')
            )
            img.paste(traveler, (90, 60), traveler)

        char_element = Image.open('./static/images/element.png').convert('RGBA')
        char_img = (
            Image.open(char_img_path).resize((150, 150), Image.BILINEAR).convert('RGBA')
        )
        char_element.paste(char_img, (4, 4), char_img)
        char_txt = ImageDraw.Draw(char_element)
        char_txt.text(
            (6, 2),
            f"C{character['actived_constellation_num']}",
            '#9575cd',
            set_font(20),
        )
        # w, h = char_txt.textsize(character['name'], set_font(20))
        # char_txt.text(
        #     ((159 - w) / 2, (150 - h)),
        #     character['name'],
        #     '#fff',
        #     set_font(20),
        # )
        char_txt.text(
            (50, 165),
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

    bottom_img = Image.open('./static/images/card-new-bottom.png').convert('RGBA')
    img = concat_img(img, bottom_img)

    file = BytesIO()
    img.save(file, format='png')
    img.close()
    file.seek(0)

    return file


async def draw_char_img(uid: int, character: dict) -> BytesIO:
    char_img_path = await get_img_path(
        SourceType.Character, character['id'], character['image']
    )
    char_img = Image.open(char_img_path).convert('RGBA')
    w, h = char_img.size
    img = Image.new(
        'RGBA',
        (w + 240, h + 60),
        ELEMENT_COLORS.get(character['element'], '#B3B3B3'),
    )
    background = Image.new(
        'RGBA',
        (w + 200, h + 20),
        ELEMENT_BACKGROUND_COLORS.get(character['element'], '#B3B3B3'),
    )
    img.paste(background, (20, 20))
    img.paste(char_img, (200, 40), char_img)

    # base info
    element_img = Image.open(
        f"./static/genshin/elements/{character['element']}.png"
    ).convert('RGBA')
    element_color = ELEMENT_COLORS.get(character['element'], '#000')
    img.paste(element_img, (40, 40), element_img)
    text_draw = ImageDraw.Draw(img)
    text_draw.text(
        (w + 40, h + 10), f'UID.{uid}', fill=element_color, font=set_font(20)
    )
    text_draw.text(
        (120, 40),
        f"{'★' * character['rarity']}",
        fill='#FFD942',
        font=set_font(40),
    )
    text_draw.text(
        (120, 100),
        f"{character['name']}",
        fill=element_color,
        font=set_font(50),
    )
    w, h = text_draw.textsize(character['name'], font=set_font(50))
    text_draw.text(
        (w + 130, 118),
        f"Lv.{character['level']}",
        fill=element_color,
        font=set_font(34),
    )
    text_draw.text(
        (120, 170),
        f" 命座 · {character['actived_constellation_num']} · 好感 · {character['fetter']}",
        fill=element_color,
        font=set_font(26),
    )

    # weapon
    item_img = Image.new('RGBA', (80, 80))
    item_draw = ImageDraw.Draw(item_img)
    item_draw.rounded_rectangle((0, 0, 80, 80), radius=10, fill=element_color)
    weapon = character['weapon']
    weapon_img_path = await get_img_path(
        SourceType.Weapon, weapon['id'], weapon['icon']
    )
    weapon_img = Image.open(weapon_img_path).resize((80, 80)).convert('RGBA')

    item_img.paste(weapon_img, (0, 0), weapon_img)
    item_draw.text(
        (2, 2), f"+{weapon['level']}·精{weapon['affix_level']}", font=set_font(12)
    )
    w, h = item_draw.textsize(f"{'★' * weapon['rarity']}", set_font(14))
    item_draw.text(
        ((80 - w) / 2, (80 - h - 2)),
        f"{'★' * weapon['rarity']}",
        fill='#FFD942',
        font=set_font(14),
    )
    img.paste(item_img, (120, 360), item_img)

    # artifacts
    artifacts = character['reliquaries']
    pos_x, pos_y = 120, 480
    for artifact in artifacts:
        item_img = Image.new('RGBA', (80, 80))
        item_draw = ImageDraw.Draw(item_img)
        item_draw.rounded_rectangle((0, 0, 80, 80), radius=10, fill=element_color)
        artifact_img_path = await get_img_path(
            SourceType.Artifact, artifact['id'], artifact['icon']
        )
        artifact_img = Image.open(artifact_img_path).resize((80, 80)).convert('RGBA')
        item_img.paste(artifact_img, (0, 0), artifact_img)
        item_draw.text((2, 2), f"+{artifact['level']}", font=set_font(12))
        w, h = item_draw.textsize(f"{'★' * artifact['rarity']}", set_font(14))
        item_draw.text(
            ((80 - w) / 2, (80 - h - 2)),
            f"{'★' * artifact['rarity']}",
            fill='#FFD942',
            font=set_font(14),
        )
        img.paste(item_img, (pos_x, pos_y), item_img)
        pos_y += 100

    file = BytesIO()
    img.save(file, format='png')
    img.close()
    file.seek(0)

    return file


async def read_cache(cache_path: Path) -> Tuple[bool, dict]:
    outdated = True
    data = {}
    now = datetime.now()
    if cache_path.is_file():
        async with aiofiles.open(cache_path, 'r', encoding='utf8') as f:
            contents = await f.read()
        contents = json.loads(contents)
        if now - timedelta(hours=1) < datetime.fromtimestamp(contents['updated']):
            outdated = False
            data = contents['data']
            log.info(f'read cache file: {cache_path}')

    return outdated, data


async def get_user_stats(uid: int) -> dict:
    cache_path = Path(f'./cache/stats_{uid}.json')
    outdated, data = await read_cache(cache_path)

    if outdated:
        log.info(f'search user stats: {uid}')
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

        stats = {'updated': datetime.now().timestamp(), 'data': data}
        async with aiofiles.open(cache_path, 'w', encoding='utf8') as f:
            await f.write(json.dumps(stats))

    return data


async def get_user_characters(uid: int) -> list:
    cache_path = Path(f'./cache/characters_{uid}.json')
    outdated, data = await read_cache(cache_path)

    if outdated:
        log.info(f'search user characters: {uid}')
        stats = await get_user_stats(uid)
        character_ids = [i['id'] for i in stats['avatars']]
        server = gs.recognize_server(uid)
        cn = is_chinese(uid)
        gs.set_cookie(
            ltuid=MIHOYO_COOKIE_LTUID if cn else HOYOLAB_COOKIE_LTUID,
            ltoken=MIHOYO_COOKIE_LTOKEN if cn else HOYOLAB_COOKIE_LTOKEN,
        )
        data = await gs.asyncify(
            gs.fetch_endpoint,
            "game_record/genshin/api/character",
            chinese=cn,
            method='POST',
            json=dict(character_ids=character_ids, role_id=uid, server=server),
            headers={'x-rpc-language': 'zh-cn'},
        )
        stats = {'updated': datetime.now().timestamp(), 'data': data}
        async with aiofiles.open(cache_path, 'w', encoding='utf8') as f:
            await f.write(json.dumps(stats))

    return data['avatars']


async def genshin_user_info(uid: int) -> Tuple[str, str, BytesIO]:
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
        log.error(str(e))
        msg = '查询出错'

    return msg, filename, file


async def genshin_user_character(
    uid: int, character_name: str
) -> Tuple[str, str, BytesIO]:
    msg = ''
    filename = f'{uid}_{character_name}.png'
    file = BytesIO()
    character_id = GENSHIN_CHARACTER_ID.get(character_name.lower())
    try:
        if not character_id:
            raise gs.errors.GenshinStatsException(f'没有**{character_name}**，请输入正确的角色名')

        user_characters = await get_user_characters(uid)
        for character in user_characters:
            if character['id'] == character_id:
                log.info(f"uid[{uid}]: {character['name']}[{character['id']}]")
                file = await draw_char_img(uid, character)
                break
        else:
            msg = f'用户[{uid}] 无此角色'
    except gs.errors.AccountNotFound:
        msg = '查无此用户。'
    except gs.errors.DataNotPublic:
        msg = '该用户隐藏了自己的秘密。'
    except gs.errors.GenshinStatsException as e:
        msg = e.msg
    except Exception as e:
        log.error(str(e))
        msg = '查询出错'

    return msg, filename, file
