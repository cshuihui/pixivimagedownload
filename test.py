import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def test_pixiv_with_headers():
    proxies = {
        'http': 'http://127.0.0.1:7890',  # 你的代理
        'https': 'http://127.0.0.1:7890'
    }

    # 完整的浏览器请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

    # 创建带重试的 session
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[403, 429, 500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        # 先访问首页
        response = session.get(
            'https://www.pixiv.net',
            headers=headers,
            proxies=proxies,
            timeout=(10, 30)
        )
        print(f"✅ Pixiv 首页访问成功，状态码: {response.status_code}")

        # 再尝试访问 API
        response2 = session.get(
            'https://www.pixiv.net/ajax/illust/123456',  # 示例 API
            headers=headers,
            proxies=proxies,
            timeout=(10, 30)
        )
        print(f"✅ Pixiv API 访问成功")

    except Exception as e:
        print(f"❌ 仍然失败: {e}")


if __name__ == "__main__":
    test_pixiv_with_headers()