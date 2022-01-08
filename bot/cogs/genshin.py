import asyncio
from datetime import datetime
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
from disnake.ext import commands, tasks
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
    pos_worlds = {
        1: [(900, 700), (900, 764)],  # 蒙德
        2: [(400, 700), (400, 764)],  # 璃月
        3: [(900, 548), (900, 610)],  # 龙脊雪山
        4: [(400, 548), (320, 610)],  # 稻妻
    }
    for world in data.explorations:
        if pos_world := pos_worlds.get(world.id):
            text_draw.text(
                pos_world[0],
                f"{world.explored / 10}%",
                "#fff",
                set_font(24),
            )
            text_draw.text(
                pos_world[1],
                f"Lv.{world.level}",
                "#fff",
                set_font(24),
            )
            if world.id == 4:
                text_draw.text(
                    (462, 610),
                    f"Lv.{world.offerings[0].level}",
                    "#fff",
                    set_font(24),
                )

    for character in data.characters[::-1]:
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
        """Same method as the parent class,
        but allows the `aiohttp.ClientSession` to use the system proxy.
        It's useful when requesting `https://bbs-api-os.mihoyo.com/`
        from China raises `403 Forbidden`.
        """
        if clear:
            self.sessions.clear()

        if isinstance(cookie_list, str):
            with open(cookie_list) as file:
                cookie_list = json.load(file)

            if not isinstance(cookie_list, list):
                raise RuntimeError("Json file must contain a list of cookies")

        for cookies in cookie_list:
            session = aiohttp.ClientSession(
                cookies=SimpleCookie(cookies), trust_env=True
            )
            self.sessions.append(session)

        return self.cookies

    def switch_session(self):
        if len(self.sessions) > 1:
            session = self.sessions.pop(0)
            self.sessions.append(session)


class Genshin(BaseCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.genshin_client = CustomGenshinClient(debug=True)
        if not (cookies := os.getenv("GENSHIN_COOKIES")):
            raise Exception("Please set your `GENSHIN_COOKIES` in `.env`.")
        self.genshin_client.set_cookies(cookies.split("#"))

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

        self.note_channel = None
        self.note_channel_id = None
        if note_channel_id := os.getenv("GENSHIN_NOTE_CHANNEL_ID"):
            self.note_channel_id = int(note_channel_id)
            self.note_task.start()

    def cog_unload(self) -> None:
        self.note_task.cancel()
        asyncio.create_task(self.genshin_client.close())

    @commands.command(name="u", help="查询游戏账号信息")
    async def genshin_user(self, ctx: commands.Context, uid: int):
        start = time.perf_counter()
        msg, filename, file = await self.create_genshin_user_data(uid)
        if msg:
            await ctx.send(msg)
        else:
            await ctx.send(file=disnake.File(file, filename=filename))

        self.logger.info(
            f"User[{ctx.author}] request Genshin[{uid}] "
            f"costed: {time.perf_counter() - start:.2f}s"
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
            f"User[{ctx.author}] request Genshin[{uid}] Character[{name}] "
            f"costed: {time.perf_counter() - start:.2f}s"
        )

    @commands.is_owner()
    @commands.command(name="n", help="查询原神实时便笺")
    async def genshin_note(self, ctx: commands.Context):
        embed = await self.create_genshin_note_data()
        await ctx.send(embed=embed)

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
            f"User[{inter.author}] request Genshin[{uid}] "
            f"costed: {time.perf_counter() - start:.2f}s"
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
            f"User[{inter.author}] request Genshin[{uid}] Character[{character_name}] "
            f"costed: {time.perf_counter() - start:.2f}s"
        )

    @commands.is_owner()
    @genshin.sub_command()
    async def note(self, inter: disnake.AppCmdInter):
        await inter.response.defer()
        embed = await self.create_genshin_note_data()
        await inter.edit_original_message(embed=embed)

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
            self.logger.error(e)

        return msg, filename, file

    @tasks.loop(hours=2)
    async def note_task(self):
        embed = await self.create_genshin_note_data()
        await self.note_channel.send(embed=embed)

    @note_task.before_loop
    async def before_note_task(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(self.note_channel_id)  # type: ignore
        if isinstance(channel, disnake.TextChannel):
            self.note_channel = channel
        else:
            self.note_task.cancel()
            self.logger.warning(
                f"GENSHIN_NOTE_CHANNEL_ID: {self.note_channel_id} is not a <TextChannel>. "
                "Note task was cancelled."
            )

    async def search_genshin_user(self, uid: int) -> PartialUserStats:
        key = f"bot:genshin:user:{uid}"
        stats = await self.redis_session.get(key)
        if stats:
            stats = PartialUserStats(**json.loads(stats))
        else:
            stats = await self.genshin_client.get_partial_user(uid, lang="zh-cn")
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
            self.logger.error(e)
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
        if len(characters) > 1:
            raise GenshinCogError(
                f"查询到多个角色，要找的是不是 **{'**, **'.join(c.name for c in characters)}**"
            )

        try:
            key = f"bot:genshin:character:{uid}:{characters[0].id}"
            character = await self.redis_session.get(key)
            if character:
                character = Character(**json.loads(character))
            else:
                character = await self.genshin_client.get_characters(
                    uid, [characters[0].id], lang="zh-cn"
                )
                character = character[0]
                await self.redis_session.set(key, json.dumps(character.dict()), ex=3600)

            # The missing images.
            if character.id not in self.static["characters"]:
                await self.q.put(("characters", character.id, character.image))
            if character.weapon.id not in self.static["weapons"]:
                await self.q.put(
                    ("weapons", character.weapon.id, character.weapon.icon)
                )
            for artifact in character.artifacts:
                if artifact.id not in self.static["artifacts"]:
                    await self.q.put(("artifacts", artifact.id, artifact.icon))

        except genshin.errors.GenshinException as e:
            if e.msg.startswith("User does not have"):
                raise GenshinCogError(f"用户[**{uid}**] 无此角色")
            else:
                raise

        return character

    async def create_genshin_note_data(self) -> disnake.Embed:
        embed = disnake.Embed(title="实时便笺", timestamp=datetime.now())
        embed.set_author(
            name="Genshin",
            url="https://webstatic-sea.hoyolab.com/app/community-game-records-sea#/ys",
            icon_url="https://img-static.mihoyo.com/avatar/avatar1.png",
        )

        for _ in self.genshin_client.sessions:
            record_card = await self.genshin_client.get_record_card()
            notes = await self.genshin_client.get_notes(record_card.uid)
            embed.add_field(
                f"{record_card.nickname}",
                f"{record_card.server_name} Lv.{record_card.level}",
                inline=False,
            )
            embed.add_field(
                f"源粹树脂",
                f"`{notes.current_resin}/{notes.max_resin}` "
                f"({disnake.utils.format_dt(notes.resin_recovered_at, style='R')}"
                f"<{notes.resin_recovered_at:%m-%d %H:%M}> 恢复)",
                inline=False,
            )
            embed.add_field(
                "每日委托", f"`{notes.completed_commissions}/{notes.max_comissions}\n`"
            )
            embed.add_field(
                "值得铭记的强敌",
                f"`{notes.remaining_resin_discounts}/{notes.max_resin_discounts}\n`",
            )
            embed.add_field(
                "探索派遣",
                f"`{sum(i.finished for i in notes.expeditions)}/{notes.max_expeditions}\n`",
            )
            embed.add_field(f"{'-' * 40}", "\u200b")

            self.genshin_client.switch_session()

        embed.remove_field(-1)

        return embed

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

        user_stats_image = await loop.run_in_executor(executor, concat_images, images)

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
        await resp.release()
        self.static[image_type].append(id)
        self.logger.debug(
            f"Download [{self.image_dir}{image_type}/{id}.png] "
            f"succeed: {data[0]}[{data[1]}]: {data[2]}."
        )


def setup(bot):
    bot.add_cog(Genshin(bot))
