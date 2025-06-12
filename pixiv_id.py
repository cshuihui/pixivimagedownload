import requests
from pixivpy3 import AppPixivAPI
import time

def id_save(name, page, phpsessid):
    url = f'https://www.pixiv.net/ajax/search/artworks/{name}?word=nahida&order=date_d&p='

    cookies = f"PHPSESSID={phpsessid}"
    headers = {
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.pixiv.net/",
        'Cookie': cookies
    }
    id_list = []

    print(f'正在获取第 {page} 页的pid')
    response = requests.get(url=url + str(page), headers=headers)
    json_data = response.json()  # json()来自requests可以自动将json解析成字典

    if response.status_code == 200:

        if type(json_data['body']) is not dict:     # 似乎到一定页数会输出空列表
            print(json_data['body'])

        else:
            for item in json_data['body']['illustManga']["data"]:
                id_list.append(item['id'])

        print('获取完成！')
    else:
        print('获取失败,状态码：', response.status_code)

    time.sleep(1)
    return id_list


if __name__ == '__main__':
    phpsessid = "78166549_F5nPs6AxBOnQzd09d7wdEd5w63c94OSp"
    print(id_save('nahida', page=1, phpsessid=phpsessid))
