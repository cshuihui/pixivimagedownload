import time

import requests
import pixiv_id


def link_find(phpsessid, pid_list=[]):
    if len(pid_list) == 0:
        print('pid为空')
        return

    print('开始获取pid直链')

    cookies = f"PHPSESSID={phpsessid}"
    link_list = []

    for pid in pid_list:
        print(f'正在获取pid为 {pid} 的链接')
        time.sleep(0.5)

        headers = {
            "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.0.0 Safari/537.36",
            "Referer": f"https://www.pixiv.net/artworks/{pid}",
            'Cookie': cookies
        }

        image_url = 'https://www.pixiv.net/ajax/illust/'
        response = requests.get(url=image_url + str(pid), headers=headers)
        # json_data = response.json()   # json()来自requests可以自动将json解析成字典

        if response.status_code == 200:
            link_list.append(response.json()['body']['urls']["original"])
            print("获取成功！准备获取下一个…")
        else:
            print('获取失败,状态码：', response.status_code)

    return link_list


if __name__ == '__main__':

    pid_list = pixiv_id.id_save("nahida")
    time.sleep(1)
    link_find(pid_list)

