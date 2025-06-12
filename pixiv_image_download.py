import requests
import pixiv_id
import pixiv_image
import time
import os


def true_page(page_input):
    for i in page_input:
        if not i.isnumeric():
            return True


def user_input():
    search_content = input('输入你要搜索的内容:')

    while 1:
        start_page = input("输入起始页:")
        if true_page(start_page):
            print('起始页格式错误！请重新输入')
            time.sleep(1)
            continue
        break

    while 1:
        last_page = input("输入结束页:")

        if true_page(last_page):
            print('结束页格式错误！请重新输入')
            time.sleep(1)
            continue
        break

    return search_content, int(start_page), int(last_page)
    # 在 while 里定义的变量 start_page，它其实是整个函数 user_input() 的局部变量。


def image_download(name, phpsessid, start_page=1, last_page=1):
    save_dir = 'download'
    sub_dir = os.path.join(save_dir, name)  # download/nahida
    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(sub_dir, exist_ok=True)

    for pages in range(start_page, last_page + 1):
        time.sleep(2)
        pid_list = pixiv_id.id_save(name, pages, phpsessid)
        print(pid_list)
        time.sleep(2)
        link_list = pixiv_image.link_find(phpsessid, pid_list)

        print(f"正在下载第 {pages} 页的图片")
        headers = {
            "Referer": "https://www.pixiv.net/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.0.0 Safari/537.36",
        }

        for img_url in link_list:
            image_name = img_url.split(sep='/')[-1]
            print(f"正在下载 {image_name} ")
            time.sleep(0.5)

            try:
                response = requests.get(img_url, headers=headers, timeout=10)

                if response.status_code == 200:

                    with open(sub_dir + '/' + image_name, "wb") as f:
                        f.write(response.content)
                    print(image_name, '下载成功！')
                else:
                    print("请求失败,状态码", response.status_code)
            except requests.exceptions.Timeout:
                print("请求超时!")
            except requests.exceptions.RequestException as e:
                print(f"请求错误, 错误信息: {e}")

    print("下载完成！")


if __name__ == "__main__":
    phpsessid = "78166549_F5nPs6AxBOnQzd09d7wdEd5w63c94OSp"
    while 1:
        search_content, start_page, last_page = user_input()

        image_download(search_content, phpsessid, start_page=start_page, last_page=last_page)

        while 1:
            choose = input('是否继续搜索？(Y/N)')
            choose.lower()
            if choose == 'y':
                break
            elif choose == 'n':
                exit()
            else:
                print("无效命令！")
