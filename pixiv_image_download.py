import requests
import pixiv_id
import pixiv_imagelink
import time
import os
import random

save_dir = 'download'
R18_rem = 0
R18G_rem = 0


def link_to_image(sub_dir, image_name, pid_link):
    headers = {
        'sec-ch-ua-platform': '"Windows"',
        "Referer": "https://www.pixiv.net/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
        'accept': 'application/json'
    }
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
    for i in range(1, 4):

        try:
            response = requests.get(pid_link, headers=headers, timeout=10, cookies=cookies)
            if response.status_code == 200:

                with open(sub_dir + '/' + image_name, "wb") as f:
                    f.write(response.content)
                print(image_name, '下载成功！')
                time.sleep(random.uniform(0.5, 1.5))
                return True
            else:
                print("请求失败,状态码", response.status_code)
                print(f"正在进行第{i}次尝试...")
                time.sleep(random.uniform(0.5, 1.5))

        except requests.exceptions.Timeout:
            print("请求超时!")
        except requests.exceptions.RequestException as e:
            print(f"请求错误, 错误信息: {e}")
    return False


def true_page(page_input):
    for i in page_input:
        if not i.isnumeric():
            return True


def user_input():
    while 1:
        search_content = input('输入你要搜索的内容:')
        if search_content == '':
            continue
        break
    while 1:
        r18_rem = input('R18标签标记（0/1）:')
        if r18_rem == '':
            r18_rem = 0
            break
        elif int(r18_rem) != 1 and int(r18_rem) != 0:
            print('标签格式错误！请重新输入')
            continue
        break
    while 1:
        r18g_rem = input('R18G标签是否标记（0/1）:')

        if r18g_rem == '':
            r18g_rem = 0
            break
        elif int(r18g_rem) != 0 and int(r18g_rem) != 1:
            print('标签格式错误！请重新输入')
            continue
        break
    while 1:
        start_page = input("输入起始页(默认为1):")
        if start_page == '':
            start_page = 1
            break
        elif true_page(start_page) or int(start_page) == 0:
            print('起始页格式错误！请重新输入')
            time.sleep(1)
            continue
        break
    while 1:
        last_page = input("输入结束页(默认当前页):")
        if last_page == '':
            last_page = start_page
            break

        elif true_page(last_page):
            print('结束页格式错误！请重新输入')
            time.sleep(1)
            continue

        elif int(last_page) < int(start_page):
            print("起始页比结束页大！请重新输入")
            continue
        break

    return search_content, int(r18_rem), int(r18g_rem), int(start_page), int(last_page)
    # 在 while 里定义的变量 start_page，它其实是整个函数 user_input() 的局部变量。


def image_download(name, phpsessid, r18_rem, r18g_rem, start_page=1, last_page=1):
    sub_dir = os.path.join(save_dir, name)  # download/nahida os会自动处理是 / 还是 \
    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(sub_dir, exist_ok=True)

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
    for pages in range(start_page, last_page + 1):

        pid_list = pixiv_id.id_save(name, pages, phpsessid)
        # print(pid_list)
        print(f"正在下载第 {pages} 页的图片")
        time.sleep(random.randint(1, 3))
        for index, pid in enumerate(pid_list, start=1):
            pid_links = pixiv_imagelink.link_find(phpsessid, pid)
            if pid_links['R18'] != R18_rem or pid_links['R18G'] != R18G_rem:
                print(pid, '已过滤')
                continue
            image_name = pid_links['link'].split(sep='/')[-1]
            print(f"正在下载 {image_name} ({index}/{len(pid_list)})")
            for i in range(0, 15):
                temp_list = list(image_name)
                temp_list[image_name.find('.')-1] = str(i)
                temp_name = ''.join(temp_list)  # 列表转字符串
                print(temp_name)
                temp_link = pid_links['link'].replace(image_name, temp_name)
                if not link_to_image(sub_dir, temp_name, temp_link):
                    break

            print("下载完成！准备下载下一个…")
            time.sleep(random.uniform(0.5, 1.5))  # uniform 用于小数点之间的随机数 输出为float类型


if __name__ == "__main__":
    with open("phpsessid.txt", 'r') as f:
        phpsessid = f.read()
    while 1:
        search_content, R18_rem, R18G_rem, start_page, last_page = user_input()

        image_download(search_content, phpsessid, R18_rem, R18G_rem, start_page=start_page, last_page=last_page)

        while 1:
            choose = input('是否继续搜索？(Y/N)')
            choose.lower()
            if choose == 'y':
                break
            elif choose == 'n':
                exit()
            else:
                print("无效命令！")
