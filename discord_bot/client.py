import os
import random
from pathlib import Path

import discord
from discord import client
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env', encoding='utf8')

TOKEN = os.getenv('DISCORD_TOKEN')


class CustomClient(discord.Client):
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')

    async def on_member_join(self, member):
        await member.create_dm()
        await member.dm_channel.send(f'Hi {member.name}, welcome to my Discord server!')

    async def on_message(self, message):
        if message.author == self.user:
            return

        brooklyn_99_quotes = [
            'I\'m the humen form of the 💯 emoji.',
            'Bingpot',
            'Cool. Cool cool cool, no doubt no doubt no doubt ',
        ]

        if message.content == '99!':
            response = random.choice(brooklyn_99_quotes)
            await message.channel.send(response)
        elif message.content == 'raise-exception':
            raise discord.DiscordException

    async def on_error(self, event, *args, **kwargs):
        with open('err.log', 'a', encoding='utf8') as f:
            if event == 'on_message':
                f.write(f'Unhandled message: {args[0]}\n')
            else:
                raise


client = CustomClient()
client.run(TOKEN)
