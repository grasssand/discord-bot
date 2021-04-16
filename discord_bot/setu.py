import os
import random
from io import BytesIO
from pathlib import Path
from typing import Tuple

import requests

SETU_KEY = os.getenv('SETU_KEY')


def get_local_img() -> Path:
    dir = Path('.')
    files = list(dir.glob('**/*'))
    img = random.choice(files)
    return img


def download_img(url: str) -> bytes:
    headers = {
        'Referer': 'https://www.pixiv.net/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36 Edg/89.0.774.68',
    }
    resp = requests.get(url, headers=headers)
    return resp.content


def get_setu(keyword: str) -> Tuple[str, str, BytesIO]:
    url = 'https://api.lolicon.app/setu/'
    params = {'apikey': SETU_KEY, 'r18': 2, 'num': 1}
    if keyword:
        params['keyword'] = keyword
    resp = requests.get(url, params=params)
    json_data = resp.json()
    print(json_data)

    msg = ''
    filename = ''
    file = BytesIO()
    if json_data['code'] == 0:
        data = json_data['data'][0]
        msg = (
            f">>> *Source:* <https://www.pixiv.net/artworks/{data['pid']}>\n"
            f"*Title:* {data['title']}\n"
            f"*Author:* {data['author']}\n"
            f"*Tags:* {'|'.join(data['tags'])}"
        )
        filename = data['url'].split('/')[-1]
        file = BytesIO(download_img(data['url']))

    return msg, filename, file
