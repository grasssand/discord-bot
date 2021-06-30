from io import BytesIO
from typing import Tuple

import aiohttp

from discord_bot.logger import logger

URL = 'https://api.lolicon.app/setu/v2'

log = logger(__name__)


async def fetch_img(session: aiohttp.ClientSession, url: str) -> bytes:
    headers = {
        'Referer': 'https://www.pixiv.net/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36 Edg/89.0.774.68',
    }
    async with session.get(url, headers=headers) as resp:
        return await resp.read()


async def get_setu(r18: int = 0, keyword: str = '') -> Tuple[str, str, BytesIO]:
    msg = ''
    filename = ''
    file = BytesIO()

    params = {'r18': r18, 'size': ['original', 'regular']}
    if keyword:
        params['tag'] = keyword.split(',')
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, json=params) as resp:
            json_data = await resp.json()
            log.info(json_data)

            if json_data['data']:
                data = json_data['data'][0]
                img_url = data['urls']['regular']
                msg = (
                    f">>> *Source:* <https://www.pixiv.net/artworks/{data['pid']}>\n"
                    f"*Title:* {data['title']}\n"
                    f"*Author:* {data['author']}\n"
                    f"*Tags:* {'|'.join(data['tags'])}"
                )
                filename = img_url.split('/')[-1]
                img = await fetch_img(session, img_url)
                file = BytesIO(img)

    return msg, filename, file
