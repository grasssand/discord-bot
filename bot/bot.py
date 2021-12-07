import os

import aiohttp
import aioredis
import disnake
import loguru
from disnake.ext import commands
from dotenv import load_dotenv

load_dotenv()


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_session = aiohttp.ClientSession(trust_env=True)
        self.redis_session = None
        self.logger = loguru.logger

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        self.redis_session = self._create_redis_session()

        await super().start(token, reconnect=reconnect)

    async def close(self) -> None:
        await super().close()

        if self.http_session:
            await self.http_session.close()

        if self.redis_session:
            await self.redis_session.close()

    async def on_ready(self) -> None:
        self.logger.info(f"{self.user} has connected to Discord!")

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("你没有权限运行这条命令哦！")
        else:
            self.logger.error(f"{error}")

    async def on_slash_command_error(
        self, inter: disnake.AppCmdInter, exception: commands.CommandError
    ) -> None:
        await super().on_slash_command_error(inter, exception)
        self.logger.error(f"{exception}")

    def _create_redis_session(self) -> aioredis.Redis:
        return aioredis.from_url(os.environ["REDIS_URL"], decode_responses=True)
