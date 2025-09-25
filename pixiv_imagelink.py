import random
import time
import requests


def mark_r18_r18g(data):
    result = {'R18': 0, 'R18G': 0}
    for d in data:
        if d['tag'] == 'R-18':
            result['R18'] = 1
        elif d['tag'] == 'R-18G':
            result['R18G'] = 1
    return result
def link_find(phpsessid, pid):
    links = dict()
    print('开始获取pid直链')

    cookies = {
        'privacy_policy_agreement': '7',
        'privacy_policy_notification': '0',
        'PHPSESSID': f'{phpsessid}',
        'login_ever': 'yes',
        '_cfuvid': 'jVYZtt9rfVhgTI8XhlQ4tqvr4eTFlul4iorbL_pt5u0-1750922757338-0.0.1.1-604800000',
        '__cf_bm': 'P9YZKweTbQzR8FxFJ2.QDk9V1xNZ7QHt55ppCJ.YcYs-1750938795-1.0.1.1-D5ThH518RaP1fWYgzZ41dJ.7_15bjiJAmth'
                   'wyGVuhdJsXzu90wqpCGMIUdQBXD7UivnwxLYcZw2sG0aUdXIgsLPmj0qKa7GA98BwNh58.EYFPhaxda.LXGBfGxMtfsLI',
        'cf_clearance': 't0DJAEbiWF308crA1KSG7UJjZhg1ZHY8m6tg0AwQYUw-1750940233-1.2.1.1-AO0LKVkdab7nJhB7Q_jJI7E9fw.o3'
                        'm0TZB7GHrnJH1iY_5ICnIyfJKgEMMYEpOR3RCNvK29R17ViIUvj7aOO7lLnJkizJP.pcWyLStlpf2niHUncfcoQ.PIPEc'
                        'Fh06vKaFjrKNG.zys9gIBmmnY3FLmL7FQeFJ2I4QbxHMEPZK1.e5QexBiG0x.nY4vixunY7y7xbyfulV3PTLOYmI4EKxk'
                        '7mPumiDDTzf.BtnN0jZn53A__MsEGByq_7fcnhgv.Mn.U.0iGsAD_3jrGRiBpOPMQG5kUE.TJiYh7Pyhl7OSCRL2v.s'
                        'W5S3eDXz767IpNRXiaIDBOO16oWyo3wfQ7liXJ2mTHEWu9BKxaJwIoUgM',
        'FCNEC': '%5B%5B%22AKsRol96Mr97eRWudXD3Lv7jAVi6BNagvWCFvaRGzH4Kh'
                 '-lOci6hh5jjnmGdeeUDtZ83WndbyRZtywdaDKC695p7NeoN_PwldsmZy5jHzQvixJ3AL0Qh6'
                 '-LDChj5UOmnQED8Uabak_FUQVkPUhfScRtxhYTmUlYI-w%3D%3D%22%5D%5D',
    }

    print(f'正在获取pid为 {pid} 的链接')
    time.sleep(random.uniform(1, 1.5))

    headers = {
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
        "Referer": f"https://www.pixiv.net/artworks/{pid}",
    }

    image_url = 'https://www.pixiv.net/ajax/illust/'
    response = requests.get(url=image_url + str(pid), headers=headers, cookies=cookies)
    # json_data = response.json()  # json()来自requests可以自动将json解析成字典

    if response.status_code == 200:
        links.update({'link': response.json()['body']['urls']["original"]})
        links.update(mark_r18_r18g(response.json()['body']['tags']['tags']))
        print("获取成功！")
        # print(response.json()['body']['tags']['tags'])
        time.sleep(random.uniform(1, 3))
    else:
        print('获取失败,状态码：', response.status_code)

    return links


if __name__ == '__main__':
    with open("phpsessid.txt", 'r') as f:
        phpsessid = f.read()
    time.sleep(1)
    print(link_find(phpsessid, '134403445'))
