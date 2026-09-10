import requests
import time
import random


MaxTryTimes = 5
MIN_WAIT_SECONDS = 0.1
MAX_WAIT_SECONDS = 0.5

def id_save(name, page, phpsessid, stop_event=None):
    """获取作品ID列表

    Args:
        name: 搜索关键词
        page: 页码
        phpsessid: PHPSESSID
        stop_event: 可选，threading.Event，设置后可在重试时响应停止信号
    """
    url = f'https://www.pixiv.net/ajax/search/artworks/{name}?word={name}&order=date_d&p='

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
    headers = {
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.pixiv.net/",
    }
    id_list = []
    session_error = None  # 会话/登录类错误原因（最终抛出真实原因，避免误报“没有找到图片”）

    print(f'正在获取第 {page} 页的pid')
    time.sleep(random.uniform(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS))
    for times in range(1, MaxTryTimes + 1):
        # 检查停止信号
        if stop_event is not None and stop_event.is_set():
            print("已收到停止信号，中断获取 PID")
            break
        try:
            response = requests.get(url=url + str(page), headers=headers, cookies=cookies, timeout=(10, 60))
            #   连接10秒 读取5秒

            response.raise_for_status()  # 主动出发异常才会被try捕捉

            json_data = response.json()  # json()来自requests可以自动将json解析成字典

            # Pixiv 返回 error=true：登录状态大概率已失效（PHPSESSID 过期）
            if json_data.get('error'):
                msg = json_data.get('message') or '未知错误'
                session_error = (f"Pixiv 返回错误：{msg} —— PHPSESSID 可能已过期，"
                                 f"请到「设置」→「PHPSESSID」重新获取或更新")
                print(session_error)
                break  # 会话失效为持续状态，无需再重试

            body = json_data.get('body')

            if not isinstance(body, dict):  # 似乎到一定页数会输出空列表
                print(json_data['body'])
                break  # 已到末尾 / 无更多结果

            for item in body['illustManga']["data"]:
                id_list.append(item['id'])

            print(f'获取完成！共{len(id_list)}个pid.')
            # print(type(id_list[0]))
            time.sleep(random.uniform(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS))
            break

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 401:
                session_error = ("PHPSESSID 已过期或无效（HTTP 401），"
                                 "请到「设置」→「PHPSESSID」重新获取或更新")
                print(session_error)
                break  # 不建议继续重试，直接跳出
            elif status == 403:
                session_error = ("访问被拒绝（HTTP 403）：可能触发 Pixiv 风控或 Cookie/PHPSESSID 已过期，"
                                 "请到「设置」重新获取 PHPSESSID（并检查代理/网络）后重试")
                print(session_error)
                break
            else:
                print(f'HTTP错误：{status}, 信息: {e}')
            time.sleep(random.uniform(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS))
        except requests.exceptions.Timeout as e:
            print("连接超时！错误信息：", e)
            time.sleep(random.uniform(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS))
        except requests.exceptions.ConnectionError as e:
            print("连接被断开或拒绝，错误信息：", e)
            time.sleep(random.uniform(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS))
        except Exception as e:
            print("发生其他错误：", e)
        print(f"正在尝试重连..({times}/{MaxTryTimes})")

    random.shuffle(id_list)  # 打乱列表元素顺序

    # 一个 PID 都没取到且明确是会话/登录错误 → 抛出真实原因，而不是静默返回空列表
    if not id_list and session_error:
        raise RuntimeError(session_error)
    return id_list

def user_works_id(user_id, php):
    import json
    import re
    # user_id = '18208231'

    def extract_username_from_html(html):
        # 从title提取
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)  # 忽视大小写
        if title_match:
            title = title_match.group(1).strip()
            # 格式: "用户名 - pixiv"
            if ' - pixiv' in title:
                return title.replace(' - pixiv', '').strip()
        return None

    api = f'https://www.pixiv.net/ajax/user/{user_id}/profile/all'
    output = dict()
    url = f"https://www.pixiv.net/users/{user_id}"
    headers = {
            "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://www.pixiv.net/",
        }
    cookies = {
        'privacy_policy_agreement': '7',
        'privacy_policy_notification': '0',
        'PHPSESSID': f'{php}',
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
    resp = requests.get(
        url=api,
        headers=headers,
        cookies=cookies,
        timeout=(10, 30)
    )
    # 会话失效/访问被拒时先给出明确原因
    if resp.status_code in (401, 403):
        reason = "PHPSESSID 已过期或无效" if resp.status_code == 401 else "访问被拒绝/触发 Pixiv 风控"
        raise RuntimeError(f"{reason}（HTTP {resp.status_code}），请到「设置」→「PHPSESSID」重新获取或更新后重试")
    if resp.status_code != 200:
        raise RuntimeError(f"获取作者作品失败：HTTP {resp.status_code}")

    try:
        result = resp.json()
    except ValueError:
        raise RuntimeError("获取作者作品返回内容异常（可能登录状态失效/PHPSESSID 过期），请到「设置」更新后重试")
    # print(result)
    
    # 检查 API 返回是否正常
    if result.get('error'):
        msg = result.get('message', '未知错误')
        raise RuntimeError(f"API 返回错误：{msg}（PHPSESSID 可能已过期），请到「设置」→「PHPSESSID」重新获取或更新")
    
    body = result.get('body')
    if not body or not isinstance(body, dict):
        raise Exception("作者不存在或API返回格式异常")
    
    illusts = body.get('illusts')
    if not illusts:
        raise Exception("该作者没有公开作品")
    
    ids = list(illusts.keys())
    output.update(WorkIds = ids)

    pickup = body.get('pickup')
    if pickup and isinstance(pickup, list) and len(pickup) > 0:
        user_name = pickup[0].get('userName', '')
    else:
        print('User does not have pickups.')
        result2 = requests.get(
            url=url,
            headers=headers,
            cookies=cookies
        )
        # print(result2)
        user_name = extract_username_from_html(result2.text)
    # 确保 user_name 不为 None
    if user_name is None:
        user_name = str(user_id)
    output.update(UserName = user_name)
    
    return output
    
    

if __name__ == '__main__':
    with open("phpsessid.txt", 'r') as f:
        phpsessid = f.read()
    user_id = '87596369'
    # number = list(range(1, 10))
    # # random.shuffle(number)
    # for i in number:
    #     print(id_save('jufufu', page=i, phpsessid=phpsessid))
    
    print(user_works_id(user_id, phpsessid))

