import importlib
import inspect
import os
import pkgutil
from pathlib import Path

import disnake

from . import cogs
from .bot import Bot

DISCORD_COMMAND_PREFIX = os.getenv("DISCORD_COMMAND_PREFIX", "!!")

intents = disnake.Intents.default()
intents.bans = False
intents.integrations = False
intents.invites = False
intents.presences = False
intents.typing = False
bot = Bot(
    command_prefix=DISCORD_COMMAND_PREFIX,
    activity=disnake.Game(f"{DISCORD_COMMAND_PREFIX}help"),
    intents=intents,
    proxy=os.getenv("DISCORD_PROXY", None),
    test_guilds=[811193626221608980],
)


path = Path(__file__).parent.joinpath("cogs")
for cog in pkgutil.walk_packages(cogs.__path__, cogs.__name__ + "."):
    if not cog.ispkg:
        imported = importlib.import_module(cog.name)
        if inspect.isfunction(getattr(imported, "setup", None)):
            try:
                bot.load_extension(cog.name)
            except Exception as e:
                bot.logger.error(e)

bot.run(os.getenv("DISCORD_TOKEN"))
