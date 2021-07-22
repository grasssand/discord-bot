import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from discord_bot.genshin_user import genshin_user_character, genshin_user_info
from discord_bot.logger import logger
from discord_bot.setu import get_setu

load_dotenv(Path(__file__).resolve().parent.parent / '.env', encoding='utf8')

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_PROXY = os.getenv('DISCORD_PROXY')
DISCORD_COMMAND_PREFIX = os.getenv('DISCORD_COMMAND_PREFIX', '!s')

log = logger(__name__)

bot = commands.Bot(
    command_prefix=DISCORD_COMMAND_PREFIX,
    activity=discord.Game(f'{DISCORD_COMMAND_PREFIX}help'),
    proxy=DISCORD_PROXY,
)


@bot.event
async def on_ready():
    log.info(f'{bot.user.name} has connected to Discord!')


@bot.event
async def on_command_error(ctx, error):
    log.error(error)
    if isinstance(error, commands.errors.CommandInvokeError):
        await ctx.send('出问题了，休息一下吧。||不要···会坏掉的···||')


@bot.command(name='.', help='来点色图')
async def setu(ctx, keyword: str = ''):
    log.info(f'setu for {ctx.author}')
    r18 = 2 if ctx.channel.is_nsfw() else 0
    msg, filename, file = await get_setu(r18=r18, keyword=keyword)
    if msg:
        await ctx.send(msg, file=discord.File(file, filename=filename))
    else:
        await ctx.send('没有这种涩图。。||(つд⊂)这未免也太变态了吧||')


@bot.command(name='u', help='查询游戏账户')
async def genshin_user(ctx, uid: int):
    msg, filename, file = await genshin_user_info(uid)
    if msg:
        await ctx.send(msg)
    else:
        await ctx.send(file=discord.File(file, filename=filename))


@bot.command(name='c', help='查询游戏角色详情')
async def genshin_character(ctx, uid: int, character_name: str):
    msg, filename, file = await genshin_user_character(uid, character_name)
    if msg:
        await ctx.send(msg)
    else:
        await ctx.send(file=discord.File(file, filename=filename))


@bot.command(name='d', help='删除bot上条回复。不喜欢的涩图？那就跳过吧')
async def delete_last_message(ctx):
    message = await ctx.channel.history(limit=20).get(author=bot.user)
    if message:
        await message.delete()


if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
