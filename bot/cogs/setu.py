import asyncio
import os
import re
from io import BytesIO
from typing import Any, Dict, Optional, Tuple, Union

import disnake
from disnake.ext import commands, tasks

from bot.utils.base_cog import BaseCog
from bot.utils.errors import SetuCogError

SETU_API = "https://api.lolicon.app/setu/v2"
TIME_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


class Setu(BaseCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tasks = {}

    @commands.Cog.listener()
    async def on_ready(self):
        await super().on_ready()

        tasks = await self.redis_session.hgetall("bot:setu:tasks")
        for guild_id, task in tasks.items():
            channel_id, num = task.split(";")
            self._setu_task(guild_id, True, int(channel_id), int(num))

    def cog_unload(self):
        for task in self._tasks.values():
            task.cancel()

    @commands.command(name=".", help="来点涩图")
    async def setu(self, ctx: commands.Context, *, query: str = "") -> None:
        self.logger.info(f"setu for {ctx.author}")
        r18 = 2 if getattr(ctx.channel, "nsfw", 0) else 0
        msg, filename, file = await self.get_setu_source(r18, query)
        if not filename:
            await ctx.send(msg)
        else:
            await ctx.send(msg, file=disnake.File(BytesIO(file), filename))

    @commands.command(name="d", help="删除bot上条回复。不喜欢的涩图？那就跳过吧")
    async def delete_last_message(self, ctx: commands.Context):
        message = await ctx.channel.history(limit=20).get(author=self.bot.user)
        if message:
            await message.delete()

    async def get_setu_source(
        self, r18: int = 2, query: str = ""
    ) -> Tuple[str, str, bytes]:
        """Fetch the image from Pixiv."""
        msg = ""
        filename = ""
        file = b""
        try:
            setu_data = await self.fetch_setu_api(r18, query)
            msg = (
                f">>> *Source:* <https://www.pixiv.net/artworks/{setu_data['pid']}>\n"
                f"*Title:* {setu_data['title']}\n"
                f"*Author:* {setu_data['author']}\n"
                f"*Tags:* {'|'.join(setu_data['tags'])}"
            )
            url = setu_data["urls"]["regular"]
            filename = url.split("/")[-1]
            headers = {
                "Referer": "https://www.pixiv.net/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/89.0.4389.114 Safari/537.36 Edg/89.0.774.68",
            }
            async with self.http_session.get(url, headers=headers) as resp:
                file = await resp.read()
        except SetuCogError as e:
            msg = str(e)
        except Exception as e:
            self.logger.error(f"Fetching Setu error：{e}")
            msg = "出问题了，休息一下吧。||不要···会坏掉的···||"

        return msg, filename, file

    async def fetch_setu_api(self, r18: int, query: str) -> Dict[str, Any]:
        params = {"r18": r18, "size": ["original", "regular"], "proxy": ""}
        if query:
            params["tag"] = query.split(",")
        if os.getenv("DISCORD_PROXY"):
            params["proxy"] = "i.pixiv.cat"

        async with self.http_session.post(SETU_API, json=params) as resp:
            data = await resp.json()
            self.logger.debug(data)
            if not data["data"]:
                raise SetuCogError("没有这种涩图。。||(つд⊂) 这未免也太变态了吧||")

        return data["data"][0]

    @commands.check_any(
        commands.is_owner(), commands.has_guild_permissions(manage_guild=True)
    )
    @commands.command(
        name="s", help="涩图 Time! 参数是 <true/1/false/0>(开/关), [#文字频道], [间隔时间]"
    )
    async def set_setu_task(
        self,
        ctx: commands.Context,
        option: bool,
        channel: Optional[disnake.TextChannel] = None,
        interval_time: str = "1d",
    ):
        r = re.match(r"(\d+)([smhdSMHD]).*", interval_time)
        if not r:
            return await ctx.send("时间格式不对哦，是 `9s/9m/9h/9d` 这样的。")

        num, unit = r.groups()
        time = TIME_UNITS[unit.lower()] * int(num)
        result = self._setu_task(str(ctx.guild.id), option, channel, time)

        await ctx.send(result)

    async def send_setu(self, channel: disnake.TextChannel) -> None:
        r18 = 2 if getattr(channel, "nsfw", 0) else 0
        _, filename, file = await self.get_setu_source(r18)
        if filename:
            await channel.send(file=disnake.File(BytesIO(file), filename))

    def _setu_task(
        self,
        guild_id: str,
        option: bool,
        channel: Optional[Union[disnake.TextChannel, int]],
        interval_time: int,
    ) -> str:
        task = self._tasks.get(guild_id)

        if option:
            if task is None:
                task = tasks.loop(seconds=interval_time)(self.send_setu)
            if isinstance(channel, int):
                channel = self.bot.get_channel(channel)  # type: ignore

            self.logger.info(
                f"Create a Setu task in #{channel.name}, runing per {interval_time}s"
            )
            task.change_interval(seconds=interval_time)
            if task.is_running():
                task.restart(channel)
            else:
                task.start(channel)
            self._tasks[guild_id] = task
            asyncio.create_task(
                self.redis_session.hset(
                    "bot:setu:tasks", guild_id, f"{channel.id};{interval_time}"
                )
            )
            result = "现在开始色色 (＾o＾)ﾉ"
        else:
            self.logger.info(f"Setu task in [{guild_id}] canceled.")
            if task is not None:
                task.cancel()
                del self._tasks[guild_id]
                asyncio.create_task(self.redis_session.hdel("bot:setu:tasks", guild_id))
            result = "( *・ω・)✄╰ひ╯ 不可以色色"

        return result


def setup(bot):
    bot.add_cog(Setu(bot))
