import requests
import time
import random


MaxTryTimes = 5
def id_save(name, page, phpsessid):
    url = f'https://www.pixiv.net/ajax/search/artworks/{name}?word=nahida&order=date_d&p='

    cookies = {
        'first_visit_datetime_pc': '2024-07-04%2020%3A04%3A52',  # 第一次访问的时间
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
    headers = {
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.pixiv.net/",
    }
    id_list = []

    print(f'正在获取第 {page} 页的pid')
    time.sleep(random.randint(2, 4))
    for times in range(1, MaxTryTimes+1):
        try:
            response = requests.get(url=url + str(page), headers=headers, cookies=cookies, timeout=(10, 5))
            #   连接10秒 读取5秒

            response.raise_for_status()     # 主动出发异常才会被try捕捉

            json_data = response.json()  # json()来自requests可以自动将json解析成字典

            if type(json_data['body']) is not dict:     # 似乎到一定页数会输出空列表
                    print(json_data['body'])

            else:
                for item in json_data['body']['illustManga']["data"]:
                    id_list.append(item['id'])

                print(f'获取完成！共{len(id_list)}个pid.')
                time.sleep(1)
                break

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 401:
                print("未授权访问（401），请检查 cookie 或 token 是否过期")
                break  # 不建议继续重试，直接跳出
            elif status == 403:
                print("禁止访问（403），可能是权限问题或被封锁")
                break
            else:
                print(f'HTTP错误：{status}, 信息: {e}')
            time.sleep(1)
        except requests.exceptions.Timeout as e:
            print("连接超时！错误信息：", e)
            time.sleep(1)
        except requests.exceptions.ConnectionError as e:
            print("连接被断开或拒绝，错误信息：", e)
            time.sleep(1)
        except Exception as e:
            print("发生其他错误：", e)
        print(f"正在尝试重连..({times}/{MaxTryTimes})")

    random.shuffle(id_list)     # 打乱列表元素顺序
    return id_list


if __name__ == '__main__':
    phpsessid = "78166549_F5nPs6AxBOnQzd09d7wdEd5w63c94OSp"
    print(id_save('jufufu', page=1, phpsessid=phpsessid))
