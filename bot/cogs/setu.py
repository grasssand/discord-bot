import os
from io import BytesIO
from typing import Any, Dict

import disnake
from disnake.ext import commands

from bot.utils.base_cog import BaseCog
from bot.utils.errors import SetuCogError

SETU_API = "https://api.lolicon.app/setu/v2"


class Setu(BaseCog):
    @commands.command(name=".", help="来点涩图")
    async def fetch(self, ctx: commands.Context, *, query: str = "") -> None:
        """Fetch the image from Pixiv"""
        self.logger.info(f"setu for {ctx.author}")
        try:
            r18 = 2 if getattr(ctx.channel, "nsfw", 0) else 0
            setu_data = await self.get_setu_source(r18, query)
        except SetuCogError as e:
            await ctx.send(e)
        except Exception as e:
            self.logger.exception(f"Fetching Setu Api error：{e}")
            await ctx.send("出问题了，休息一下吧。||不要···会坏掉的···||")
        else:
            url = setu_data["urls"]["regular"]
            headers = {
                "Referer": "https://www.pixiv.net/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/89.0.4389.114 Safari/537.36 Edg/89.0.774.68",
            }
            try:
                resp = await self.http_session.get(url, headers=headers)
                resp.raise_for_status()
            except Exception as e:
                self.logger.exception(f"Fetching pixiv[{url}] error：{e}")
                await ctx.send("出问题了，休息一下吧。||不要···会坏掉的···||")
            else:
                file = await resp.read()
                filename = url.split("/")[-1]
                msg = (
                    f">>> *Source:* <https://www.pixiv.net/artworks/{setu_data['pid']}>\n"
                    f"*Title:* {setu_data['title']}\n"
                    f"*Author:* {setu_data['author']}\n"
                    f"*Tags:* {'|'.join(setu_data['tags'])}"
                )
                await ctx.send(msg, file=disnake.File(BytesIO(file), filename))

    async def get_setu_source(self, r18, query: str) -> Dict[str, Any]:
        """Request a setu"""
        params = {"r18": r18, "size": ["original", "regular"], "proxy": ""}
        if query:
            params["tag"] = query.split(",")
        if os.getenv("DISCORD_PROXY"):
            params["proxy"] = "i.pixiv.cat"

        async with self.http_session.post(SETU_API, json=params) as resp:
            data = await resp.json()
            self.logger.debug(data)
            if not data["data"]:
                raise SetuCogError("没有这种涩图。。||(つд⊂)这未免也太变态了吧||")

        return data["data"][0]


def setup(bot):
    bot.add_cog(Setu(bot))
