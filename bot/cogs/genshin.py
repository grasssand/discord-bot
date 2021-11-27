import asyncio
import json
import os
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional, Tuple, Union

import aiofiles
import aiohttp
import disnake
import genshin
from genshin.models.base import PartialCharacter
from genshin.models.character import Character
from genshin.models.stats import PartialUserStats
from disnake.ext import commands
from PIL import Image, ImageDraw, ImageFont

from bot.utils import database
from bot.utils.base_cog import BaseCog
from bot.utils.errors import GenshinCogError

SERVER_NAME = {
    "1": "天空岛",
    "2": "天空岛",
    "5": "世界树",
    "6": "美服",
    "7": "欧服",
    "8": "亚服",
    "9": "港澳台服",
}

ELEMENT_COLORS = {
    "Anemo": "#3C8B6D",
    "Cryo": "#5C9DAB",
    "Dendro": "#789B34",
    "Electro": "#946FAE",
    "Geo": "#A39982",
    "Hydro": "#2A8AA9",
    "Pyro": "#B07451",
}

ELEMENT_BACKGROUND_COLORS = {
    "Anemo": "#C7DDD5",
    "Cryo": "#C0E7F2",
    "Dendro": "#B4E84E",
    "Electro": "#D0CCE1",
    "Geo": "#F0E1C0",
    "Hydro": "#C5D7E3",
    "Pyro": "#ECC5C3",
}


def set_font(size: int = 20) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("./static/fonts/font.ttf", size=size)


def concat_images(images: List[Image.Image]) -> Image.Image:
    widths, heights = zip(*(i.size for i in images))

    total_width = max(widths)
    max_height = sum(heights)

    new_im = Image.new("RGBA", (total_width, max_height))

    y_offset = 0
    for im in images:
        new_im.paste(im, (0, y_offset))
        y_offset += im.size[1]

    return new_im


def draw_user_base(uid: int, data: PartialUserStats) -> Image.Image:
    server = SERVER_NAME.get(str(uid)[0], "")
    img = Image.open("./static/genshin/card/info-new-upper.png")
    text_draw = ImageDraw.Draw(img)
    text_draw.text((280, 120), f"UID {uid}", "#263238", set_font(34))
    text_draw.text((380, 170), server, "#424242", set_font(30))

    # stats
    stats = data.stats
    text_draw.text((280, 292), f"{stats.days_active}", "#263238", set_font(32))
    text_draw.text((280, 346), f"{stats.achievements}", "#263238", set_font(32))
    text_draw.text((280, 400), f"{stats.characters}", "#263238", set_font(32))
    text_draw.text((280, 452), f"{stats.spiral_abyss}", "#263238", set_font(32))
    text_draw.text((620, 292), f"{stats.common_chests}", "#263238", set_font(32))
    text_draw.text((620, 346), f"{stats.exquisite_chests}", "#263238", set_font(32))
    text_draw.text((620, 400), f"{stats.precious_chests}", "#263238", set_font(32))
    text_draw.text((620, 452), f"{stats.luxurious_chests}", "#263238", set_font(32))
    text_draw.text((960, 292), f"{stats.anemoculi}", "#263238", set_font(32))
    text_draw.text((960, 346), f"{stats.geoculi}", "#263238", set_font(32))
    text_draw.text((960, 400), f"{stats.electroculi}", "#263238", set_font(32))

    # home
    homes = data.teapot
    if homes:
        text_draw.text((1160, 145), f"仙力 {homes.comfort}", "#263238", set_font(28))
        text_draw.text((1180, 185), f"{homes.comfort_name}", "#263238", set_font(28))

    # world_explorations
    world = data.explorations
    # world = data.explorations[0]
    # id=4 稻妻
    text_draw.text(
        (400, 548),
        f"{world[0].explored / 10}%",
        "#fff",
        set_font(24),
    )
    text_draw.text(
        (320, 610),
        f"Lv.{world[0].level}",
        "#fff",
        set_font(24),
    )
    text_draw.text(
        (462, 610),
        f"Lv.{world[0].offerings[0].level}",
        "#fff",
        set_font(24),
    )
    # id=3 龙脊雪山
    text_draw.text(
        (900, 548),
        f"{world[1].explored / 10}%",
        "#fff",
        set_font(24),
    )
    text_draw.text(
        (900, 610),
        f"Lv.{world[1].level}",
        "#fff",
        set_font(24),
    )
    # id=2 璃月
    text_draw.text(
        (400, 700),
        f"{world[2].explored / 10}%",
        "#fff",
        set_font(24),
    )
    text_draw.text(
        (400, 764),
        f"Lv.{world[0].level}",
        "#fff",
        set_font(24),
    )
    # id=1 蒙德
    text_draw.text(
        (900, 700),
        f"{world[3].explored / 10}%",
        "#fff",
        set_font(24),
    )
    text_draw.text(
        (900, 764),
        f"Lv.{world[3].level}",
        "#fff",
        set_font(24),
    )

    for character in data.characters:
        if character.id in [10000005, 10000007]:
            with Image.open(f"./static/genshin/avatars/{character.id}.png").resize(
                (180, 180), Image.BILINEAR
            ) as traveler:
                img.paste(traveler, (90, 60), traveler)
                break

    return img


def chunk_list(l: List, n: int = 7):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def draw_user_characters(characters: List[PartialCharacter]) -> Image.Image:
    box_x, box_y = 110, 10
    middle = Image.open("./static/genshin/card/card-new-middle.png")
    for character in characters:
        with Image.open("./static/genshin/card/element.png") as char_element:
            with Image.open(f"./static/genshin/avatars/{character.id}.png").resize(
                (150, 150), Image.BILINEAR
            ) as char_img:
                char_element.paste(char_img, (4, 4), char_img)
                char_txt = ImageDraw.Draw(char_element)
                char_txt.text(
                    (8, 2),
                    f"C{character.constellation}",
                    "#b388ff",
                    set_font(20),
                )
                char_txt.text(
                    (50, 165),
                    f"Lv.{character.level}",
                    "#64dd17",
                    set_font(22),
                )
                char_txt.text(
                    (50, 200),
                    f"^_^{character.friendship}",
                    "#ff80ab",
                    set_font(22),
                )
                middle.paste(char_element, (box_x, box_y), char_element)
                box_x += 180

    return middle


def draw_character(uid: int, character: Character) -> Image.Image:
    time.sleep(10)
    element_color = ELEMENT_COLORS[character.element]
    size_w, size_h = 614, 1108
    img = Image.new(
        "RGBA",
        (size_w + 240, size_h + 60),
        element_color,
    )
    with Image.new(
        "RGBA",
        (size_w + 200, size_h + 20),
        ELEMENT_BACKGROUND_COLORS[character.element],
    ) as background:
        img.paste(background, (20, 20))
    with Image.open(f"./static/genshin/characters/{character.id}.png") as char_img:
        img.paste(char_img, (240, 40), char_img)
    with Image.open(
        f"./static/genshin/elements/{character.element}.png"
    ) as element_img:
        img.paste(element_img, (40, 40), element_img)

    # base info
    text_draw = ImageDraw.Draw(img)
    text_draw.text(
        (size_w + 40, size_h + 10), f"UID.{uid}", fill=element_color, font=set_font(20)
    )
    text_draw.text(
        (120, 40),
        f"{'★' * character.rarity}",
        fill="#FFD942",
        font=set_font(40),
    )
    text_draw.text(
        (120, 100),
        f"{character.name}",
        fill=element_color,
        font=set_font(50),
    )
    w, h = text_draw.textsize(character.name, font=set_font(50))
    text_draw.text(
        (w + 130, 118),
        f"Lv.{character.level}",
        fill=element_color,
        font=set_font(34),
    )
    text_draw.text(
        (120, 170),
        f" 命座 · {character.constellation} · 好感 · {character.friendship}",
        fill=element_color,
        font=set_font(26),
    )

    # weapon
    with Image.open(f"./static/genshin/weapons/{character.weapon.id}.png").resize(
        (100, 100)
    ) as weapon_img:
        img.paste(weapon_img, (40, 320), weapon_img)
    text_draw.text(
        (150, 320),
        f"{character.weapon.name}",
        fill=element_color,
        font=set_font(26),
    )
    w, h = text_draw.textsize(character.weapon.name, font=set_font(26))
    text_draw.text(
        (w + 156, h + 300),
        f"+{character.weapon.level} · 精{character.weapon.refinement}",
        fill=element_color,
        font=set_font(18),
    )
    text_draw.text(
        (150, 350),
        f"{'★' * character.weapon.rarity}",
        fill="#FFD942",
        font=set_font(22),
    )
    text_draw.text(
        (150, 376),
        "\n".join(textwrap.wrap(character.weapon.description, width=20)),
        font=set_font(12),
    )

    # artifacts
    pos_x, pos_y = 120, 480
    for artifact in character.artifacts:
        with Image.new("RGBA", (80, 80)) as item_img:
            item_draw = ImageDraw.Draw(item_img)
            item_draw.rounded_rectangle((0, 0, 80, 80), radius=10, fill=element_color)
            with Image.open(f"./static/genshin/artifacts/{artifact.id}.png").resize(
                (80, 80)
            ) as artifact_img:
                item_img.paste(artifact_img, (0, 0), artifact_img)
            img.paste(item_img, (pos_x, pos_y), item_img)
        text_draw.text(
            (pos_x + 90, pos_y),
            f"{artifact.name}",
            fill=element_color,
            font=set_font(22),
        )
        w, h = text_draw.textsize(artifact.name, font=set_font(22))
        text_draw.text(
            (pos_x + w + 96, pos_y + h - 20),
            f"+{artifact.level}",
            fill=element_color,
            font=set_font(18),
        )
        text_draw.text(
            (pos_x + 90, pos_y + 26),
            f"{'★' * artifact.rarity}",
            fill="#FFD942",
            font=set_font(22),
        )
        pos_y += 100

    return img


class CustomGenshinClient(genshin.MultiCookieClient):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def set_cookies(
        self,
        cookie_list: Union[Iterable[Union[Mapping[str, Any], str]], str],
        clear: bool = True,
    ) -> List[Mapping[str, str]]:
        """Set a list of cookies

        :param cookie_list: A list of cookies or a json file containing cookies
        :param clear: Whether to clear all of the previous cookies
        """
        if clear:
            self.sessions.clear()

        if isinstance(cookie_list, str):
            with open(cookie_list) as file:
                cookie_list = json.load(file)

            if not isinstance(cookie_list, list):
                raise RuntimeError("Json file must contain a list of cookies")

        for cookies in cookie_list:
            """
            Request `https://bbs-api-os.mihoyo.com/` will raise `403 Forbidden` in China,
            set `trust_env=True` to use the system proxy.
            """
            session = aiohttp.ClientSession(
                cookies=SimpleCookie(cookies), trust_env=True
            )
            self.sessions.append(session)

        return self.cookies


class Genshin(BaseCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gensin_client = CustomGenshinClient(debug=True)
        self.gensin_client.set_cache(maxsize=256, ttl=3600)
        self.q = asyncio.Queue()
        self.image_dir = "./static/genshin/"
        self.static = {
            "avatars": [
                int(i.stem) for i in Path(f"{self.image_dir}avatars").glob("*.png")
            ],
            "characters": [
                int(i.stem) for i in Path(f"{self.image_dir}characters").glob("*.png")
            ],
            "weapons": [
                int(i.stem) for i in Path(f"{self.image_dir}weapons").glob("*.png")
            ],
            "artifacts": [
                int(i.stem) for i in Path(f"{self.image_dir}artifacts").glob("*.png")
            ],
        }

    async def cog_load(self) -> None:
        cookies = os.getenv("GENSHIN_COOKIES")
        if not cookies:
            raise Exception("Please set your `GENSHIN_COOKIES` in `.env`.")

        cookies = cookies.split("#")
        self.gensin_client.set_cookies(cookies)

    def cog_unload(self) -> None:
        asyncio.create_task(self.gensin_client.close())

    @commands.command(name="u", help="查询游戏账号信息")
    async def genshin_user(self, ctx: commands.Context, uid: int):
        start = time.perf_counter()
        msg, filename, file = await self.create_genshin_user_data(uid)
        if msg:
            await ctx.send(msg)
        else:
            await ctx.send(file=disnake.File(file, filename=filename))

        self.logger.info(
            f"User[{ctx.author}] request Genshin[{uid}] costed: {time.perf_counter() - start:.2f}s"
        )

    @commands.command(name="c", help="查询游戏角色详情")
    async def genshin_character(self, ctx, uid: int, *character_name: str):
        name = " ".join(character_name)
        start = time.perf_counter()
        msg, filename, file = await self.create_genshin_character_data(uid, name)
        if msg:
            await ctx.send(msg)
        else:
            await ctx.send(file=disnake.File(file, filename=filename))

        self.logger.info(
            f"User[{ctx.author}] request Genshin[{uid}] Character[{character_name}] costed: {time.perf_counter() - start:.2f}s"
        )

    @commands.slash_command()
    async def genshin(self, inter: disnake.AppCmdInter):
        pass

    @genshin.sub_command()
    async def user(
        self,
        inter: disnake.AppCmdInter,
        uid: int = commands.Param(desc="游戏内 UID"),
    ):
        start = time.perf_counter()
        await inter.response.defer()

        msg, filename, file = await self.create_genshin_user_data(uid)
        if msg:
            await inter.send(msg)
        else:
            await inter.edit_original_message(
                file=disnake.File(file, filename=filename)
            )

        self.logger.info(
            f"User[{inter.author}] request Genshin[{uid}] costed: {time.perf_counter() - start:.2f}s"
        )

    @genshin.sub_command()
    async def character(
        self,
        inter: disnake.AppCmdInter,
        uid: int = commands.Param(desc="游戏内 UID"),
        character_name: str = commands.Param(desc="角色名"),
    ):
        start = time.perf_counter()
        await inter.response.defer()

        msg, filename, file = await self.create_genshin_character_data(
            uid, character_name
        )
        if msg:
            await inter.send(msg)
        else:
            await inter.edit_original_message(
                file=disnake.File(file, filename=filename)
            )

        self.logger.info(
            f"User[{inter.author}] request Genshin[{uid}] Character[{character_name}] costed: {time.perf_counter() - start:.2f}s"
        )

    async def create_genshin_user_data(self, uid: int) -> Tuple[str, str, BytesIO]:
        msg = ""
        filename = f"{uid}.png"
        file = BytesIO()
        try:
            stats = await self.search_genshin_user(uid)
            file = await self._draw_user_stats(uid, stats, file)
        except genshin.errors.AccountNotFound as e:
            msg = "查无此用户。"
        except genshin.errors.DataNotPublic as e:
            msg = "该用户隐藏了自己的秘密。"
        except Exception as e:
            msg = "查询失败。"
            self.logger.exception(e)

        return msg, filename, file

    async def search_genshin_user(self, uid: int) -> PartialUserStats:
        key = f"bot:genshin:user:{uid}"
        stats = await self.redis_session.get(key)
        if stats:
            stats = PartialUserStats(**json.loads(stats))
        else:
            stats = await self.gensin_client.get_partial_user(uid, lang="zh-cn")
            await self.redis_session.set(key, json.dumps(stats.dict()), ex=3600)

        for character in stats.characters:
            if character.id not in self.static["avatars"]:
                await self.q.put(("avatars", character.id, character.icon))

        return stats

    async def create_genshin_character_data(
        self, uid: int, character_name: str
    ) -> Tuple[str, str, BytesIO]:
        msg = ""
        filename = ""
        file = BytesIO()
        try:
            character = await self.search_genshin_character(uid, character_name)
            filename = f"{uid}_{character.name}.png"
            file = await self._draw_character(uid, character, file)
        except GenshinCogError as e:
            msg = str(e)
        except genshin.errors.AccountNotFound as e:
            msg = "查无此用户。"
        except genshin.errors.DataNotPublic as e:
            msg = "该用户隐藏了自己的秘密。"
        except Exception as e:
            msg = "查询失败。"
            self.logger.exception(e)
        return msg, filename, file

    async def search_genshin_character(
        self, uid: int, character_name: str
    ) -> Character:

        loop = asyncio.get_event_loop()
        characters = await loop.run_in_executor(
            None, database.get_character_by_name, character_name
        )

        if not characters:
            raise GenshinCogError(f"没有**{character_name}**，请输入正确的角色名")
        if len(characters) > 2:
            raise GenshinCogError(
                f"查询到多个角色，要找的是不是 **{'**, **'.join(c.name for c in characters)}**"
            )

        stats = await self.search_genshin_user(uid)
        characters_list = [c.id for c in characters]
        for c in stats.characters:
            if c.id in characters_list:
                key = f"bot:genshin:character:{uid}:{c.id}"
                character = await self.redis_session.get(key)
                if character:
                    character = Character(**json.loads(character))
                else:
                    character = await self.gensin_client.get_characters(
                        uid, [c.id], lang="zh-cn"
                    )
                    character = character[0]
                    await self.redis_session.set(
                        key, json.dumps(character.dict()), ex=3600
                    )
                if character.id not in self.static["characters"]:
                    await self.q.put(("characters", character.id, character.image))
                if character.weapon.id not in self.static["weapons"]:
                    await self.q.put(
                        ("weapons", character.weapon.id, character.weapon.icon)
                    )
                for artifact in character.artifacts:
                    if artifact.id not in self.static["artifacts"]:
                        await self.q.put(("artifacts", artifact.id, artifact.icon))

                break
        else:
            raise GenshinCogError(f"用户[**{uid}**] 无此角色")

        return character

    async def _draw_user_stats(
        self, uid: int, stats: PartialUserStats, file: BytesIO
    ) -> BytesIO:
        await self._download_images()
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor()
        images = await asyncio.gather(
            loop.run_in_executor(executor, draw_user_base, uid, stats),
            *[
                loop.run_in_executor(executor, draw_user_characters, characters)
                for characters in chunk_list(stats.characters)
            ],
            loop.run_in_executor(
                executor,
                lambda: Image.open("./static/genshin/card/card-new-bottom.png"),
            ),
        )

        user_stats_image = await loop.run_in_executor(None, concat_images, images)

        user_stats_image.save(file, format="PNG")
        file.seek(0)
        user_stats_image.close()
        for img in images:
            img.close()

        return file

    async def _draw_character(
        self, uid: int, character: Character, file: BytesIO
    ) -> BytesIO:
        await self._download_images()
        loop = asyncio.get_event_loop()
        img = await loop.run_in_executor(None, draw_character, uid, character)

        img.save(file, format="PNG")
        file.seek(0)
        img.close()

        return file

    async def _download_images(self) -> None:
        tasks = [
            asyncio.create_task(self._fetch_worker()) for _ in range(self.q.qsize())
        ]
        await asyncio.gather(*tasks)
        await self.q.join()
        for t in tasks:
            t.cancel()

    async def _fetch_worker(self) -> None:
        try:
            data = await self.q.get()
            await self._fetch(data)
            self.q.task_done()
        except asyncio.CancelledError:
            pass

    async def _fetch(self, data: Tuple[str, int, str], retry: int = 3) -> None:
        image_type, id, url = data
        tries = 0
        while tries < retry:
            try:
                resp = await self.http_session.get(url)
                resp.raise_for_status()
                break
            except Exception:
                pass

            tries += 1
        else:
            self.logger.warning(f"Failed to download {url}")
            # await asyncio.sleep(1)
            await self.q.put(data)
            return

        async with aiofiles.open(f"{self.image_dir}{image_type}/{id}.png", "wb") as f:
            await f.write(await resp.read())
        self.static[image_type].append(id)
        self.logger.debug(
            f"Download [{self.image_dir}{image_type}/{id}.png] succeed: {data[0]}[{data[1]}]: {data[2]}."
        )


def setup(bot):
    bot.add_cog(Genshin(bot))
