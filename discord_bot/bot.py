import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from discord_bot.genshin_user import get_user
from discord_bot.setu import get_setu

load_dotenv(Path(__file__).resolve().parent.parent / '.env', encoding='utf8')

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='!s', activity=discord.Game('!shelp'))


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandInvokeError):
        await ctx.send('出问题了，休息一下吧。||图太大~~塞不下了，会坏掉的~||')


@bot.command(name='.', help='来点色图')
async def setu(ctx, keyword: str = ''):
    r18 = ctx.channel.is_nsfw()
    msg, filename, file = get_setu(r18=r18, keyword=keyword)
    if msg:
        await ctx.send(msg, file=discord.File(file, filename=filename))
    else:
        await ctx.send('CD 冷却中。。。||强撸灰飞烟灭||')


@bot.command(name='u', help='查询游戏角色')
async def genshin_user(ctx, uid: int):
    msg, filename, file = get_user(uid)
    if msg:
        await ctx.send(msg)
    else:
        file.seek(0)
        await ctx.send(file=discord.File(file, filename=filename))


if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
