"""爬取 Pixiv 作品各页链接，返回二维字典 { 页码: { 图片质量: URL } }"""

import requests
import time
import random
import os

MIN_WAIT_SECONDS = 0.1
MAX_WAIT_SECONDS = 0.3


def get_phpsessid():
    """从 phpsessid.txt 读取会话ID"""
    if os.path.exists("phpsessid.txt"):
        with open("phpsessid.txt", 'r') as f:
            return f.read().strip()
    return None


def get_artwork_pages(pid, phpsessid):
    """
    获取多图作品的各页图片链接
    API: https://www.pixiv.net/ajax/illust/{pid}/pages
    返回: 二维字典 { 页码: { 图片质量: URL } }
    """
    cookies = {
        'privacy_policy_agreement': '7',
        'privacy_policy_notification': '0',
        'PHPSESSID': f'{phpsessid}',
        'login_ever': 'yes',
    }

    headers = {
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
        "Referer": f"https://www.pixiv.net/artworks/{pid}",
    }

    url = f'https://www.pixiv.net/ajax/illust/{pid}/pages'

    time.sleep(random.uniform(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS))

    response = requests.get(url=url, headers=headers, cookies=cookies, timeout=(10, 60))

    if response.status_code == 200:
        data = response.json()
        if data.get('error'):
            return None

        pages = data.get('body', [])

        url_dict = {}
        for i, page in enumerate(pages):
            url_dict[i + 1] = page.get('urls', {})

        return url_dict

    return None


if __name__ == '__main__':
    phpsessid = get_phpsessid()
    if phpsessid:
        result = get_artwork_pages('144811703', phpsessid)
        print(result)
