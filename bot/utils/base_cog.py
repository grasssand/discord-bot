from disnake.ext import commands

from ..bot import Bot


class BaseCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @property
    def http_session(self):
        return self.bot.http_session

    @property
    def redis_session(self):
        return self.bot.redis_session

    @property
    def logger(self):
        return self.bot.logger

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f"{self.__class__.__name__} cog is ready.")
