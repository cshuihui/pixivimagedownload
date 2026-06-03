import gradio as gr
import os
import shutil
from pixiv_image_download import image_download, link_to_image, filename_extract_index
from pixiv_imagelink import link_find
import numpy as np
import requests

# 👉 假设这是你爬取后的图片路径列表
image_list = []
default_image = '143035291_p0.jpg'
pids_filter_dir = 'pids_filter.txt'
with open(pids_filter_dir, 'a+') as f:  # 用a+文件指针会在文件末尾，需要将指针移到开头
    f.seek(0)
    pids_filter_list = f.read().splitlines()
    # print(pids_filter_list)
    if pids_filter_list == ['']:
        pids_filter_list = []

with open('phpsessid.txt', 'a+') as f:
    f.seek(0)
    phpsessid = f.readline().rstrip()

temp_dir = 'temp'
save_dir = "saved"
os.makedirs(save_dir, exist_ok=True)

if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
# 重新创建
os.makedirs(temp_dir, exist_ok=True)

image_list.clear()
pixiv_connect_status = {
    'connected': True,
    'not_connect': False,
}

# 🌿 当前显示图片
def get_image(index):
    if 0 <= index < len(image_list):
        return image_list[index]
    return None


# ✅ 保存图片
def save_image(index, check_box_group, search_con, php):
    if len(image_list) > index >= 0:
        img_path = image_list[index]
        temp_save_dir = os.path.join(save_dir, search_con)
        os.makedirs(temp_save_dir, exist_ok=True)

        image_filename = os.path.basename(img_path)
        idx_str = filename_extract_index(image_filename)
        pid = filename_split(image_filename)
        pid_links = link_find(php, pid, quality=4)

        # 提取页码，找不到则默认下载第1页
        image_index = int(idx_str) if idx_str is not None else 0
        page_url = pid_links['links'][image_index + 1]['original']
        page_name = page_url.split('/')[-1]
        link_to_image(temp_save_dir, page_name, page_url, php)

        pid_filter_add(pid, check_box_group)

    index = last_im_process(index)
    if index == -1:
        return -1, None, gr.update(value=[])
    index = skip_pid_filter(index)
    if index == -1:
        return -1, None, gr.update(value=[])

    return index, get_image(index), gr.update(value=[])


# ❌ 丢弃图片
def discard_image(index, check_box_group):
    if 0 <= index < len(image_list):
        pid_filter_add(filename_split(os.path.basename(image_list[index])), check_box_group)

    index = last_im_process(index)
    if index == -1:
        return -1, None, gr.update(value=[])
    index = skip_pid_filter(index)
    if index == -1:
        return -1, None, gr.update(value=[])

    return index, get_image(index), gr.update(value=[])


def search_image(content, r18_filter, r18g_filter, pages, php):
    global image_list

    if content is None or str(content).strip() == '':
        gr.Warning("请输入搜索关键词")
        return 0, default_image, gr.update(value=[])

    r18_rem = 0 if r18_filter else 1
    r18g_rem = 0 if r18g_filter else 1

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    # 重新创建
    os.makedirs(temp_dir, exist_ok=True)

    image_list.clear()

    image_download(content,
                   php,
                   r18_rem,
                   r18g_rem,
                   save_dir=temp_dir,
                   last_page=int(pages),
                   pids_filter=pids_filter_list,
                   quality=2
                   )

    im_list = os.listdir(os.path.join(temp_dir, content))
    for file in im_list:
        image_list.append(os.path.abspath(os.path.join(temp_dir, content, file)))

    index = skip_pid_filter(-1)
    if index == -1:
        return -1, None, gr.update(value=[])

    print('下载序列结束.')
    return index, get_image(index), gr.update(value=[])


def last_im_process(index):
    if len(image_list) == 0:
        return -1

    if index < -1:
        return -1

    if index >= len(image_list):
        return len(image_list) - 1

    if index == len(image_list) - 1:
        return -1

    return index


def pid_filter_add(pid, check_box_group):
    global pids_filter_list
    if pid is None:
        return
    if 'pid屏蔽' in check_box_group and pid not in pids_filter_list:
        pids_filter_list.append(pid)
        with open(pids_filter_dir, 'w') as f:
            for pid in pids_filter_list:
                f.write(str(pid) + '\n')

    return


def skip_pid_filter(index):
    for i in range(index + 1, len(image_list)):
        pid = filename_split(os.path.basename(image_list[i]))
        if pid not in pids_filter_list:
            return i
    return -1


def filename_split(filename):
    for i in ['-', '_', '.', '/', '?', '!', '&']:
        filename = filename.split(i)[0]
    return filename

def check_pixiv(php_id):
    try:
        response = requests.get(
            "https://www.pixiv.net/ajax/user/extra",
            cookies={"PHPSESSID": phpsessid},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if response.status_code == 200:
            return "✅ 连接成功", "✅ 连接成功"
        else:
            return f"❌ 连接失败，状态码: {response.status_code}", f"❌ 连接失败，状态码: {response.status_code}"
    except requests.exceptions.Timeout:
        return "❌ 连接超时", "❌ 连接超时"
    except Exception as e:
        return f"❌ 连接失败: {e}", f"❌ 连接失败: {e}"



# 🌸 UI
with gr.Blocks(title="Pixiv 图片筛选器") as demo:
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    # 重新创建
    os.makedirs(temp_dir, exist_ok=True)
    print("缓存文件夹已建立或清空")

    gr.Markdown("""
    ###总标题
    """)

    shared_phpsessid = gr.State(phpsessid)
    with gr.TabItem("筛选器"):
        with gr.Column():
            state = gr.State(0)  # 能记住状态的变量 专门用来在 UI 交互中保存数据
            with gr.Row():
                key_words = gr.Textbox(label="输入要搜索的关键词")
                search_pages = gr.Number(label="搜索页数",
                                         minimum=1,
                                         maximum=20,
                                         value=1,
                                         precision=0)
            php_textbox = gr.Textbox(label='phpsessid'.upper(), value=shared_phpsessid.value)
            with gr.Row():
                R18_rem_check = gr.Checkbox(value=True, label='R18过滤')
                R18G_rem_check = gr.Checkbox(value=True, label='R18G过滤')
            search_btn = gr.Button("搜索", variant="primary")

            with gr.Row():
                with gr.Column(scale=5):
                    image = gr.Image(type="filepath", height=800, width=1600, interactive=False)

                with gr.Column(scale=1):
                    check_boxs = gr.CheckboxGroup(
                        choices=['pid屏蔽'],
                        value=[]
                    )

            with gr.Row():
                save_btn = gr.Button("✅ 保存", variant="primary")
                discard_btn = gr.Button("❌ 丢弃", variant='stop')

            # 初始化
            demo.load(lambda: default_image, outputs=image)

            # 按钮逻辑
            save_btn.click(save_image,
                           inputs=[state, check_boxs, key_words, php_textbox],
                           outputs=[state, image, check_boxs])
            discard_btn.click(discard_image, inputs=[state, check_boxs], outputs=[state, image, check_boxs])
            search_btn.click(search_image,
                             inputs=[key_words, R18_rem_check, R18G_rem_check, search_pages, php_textbox],
                             outputs=[state, image, check_boxs])

# 变量名还是不要重复
    with gr.TabItem("纳西妲专用筛选器"):
        with gr.Column():
            state2 = gr.State(0)

            with gr.Row():
                with gr.Column(scale=5):
                    image2 = gr.Image(type="filepath", height=800, width=1600, interactive=False)

                with gr.Column(scale=1):
                    with gr.Column():
                        check_boxs2 = gr.CheckboxGroup(
                            choices=['pid屏蔽'],
                            value=[]
                        )
                        R18_rem_check2 = gr.Checkbox(value=True, label='R18过滤')
                        R18G_rem_check2 = gr.Checkbox(value=True, label='R18G过滤')
                        search_pages2 = gr.Number(label="搜索页数",
                                                  minimum=1,
                                                  maximum=20,
                                                  value=1,
                                                  precision=0)
                        search_btn2 = gr.Button("搜索", variant="primary")
            with gr.Row():
                save_btn2 = gr.Button("✅ 保存", variant="primary")
                discard_btn2 = gr.Button("❌ 丢弃", variant='stop')

            with gr.Row():
                search_box = gr.Dropdown(label="搜索内容", choices=['nahida', '纳西妲', 'ナヒーダ'], interactive=True)

                model_identify2 = gr.Checkbox(value=False, label="模型识别")

            php_textbox2 = gr.Textbox(label='phpsessid'.upper(), value=shared_phpsessid.value)

            save_filename = gr.Textbox(value='纳西妲', visible=False, interactive=False)
            search_btn2.click(search_image,
                              inputs=[search_box, R18_rem_check2, R18G_rem_check2, search_pages2, php_textbox2],
                              outputs=[state2, image2, check_boxs2])
            discard_btn2.click(discard_image, inputs=[state2, check_boxs2], outputs=[state2, image2, check_boxs2])
            save_btn2.click(save_image,
                            inputs=[state2, check_boxs2, save_filename, php_textbox2],
                            outputs=[state2, image2, check_boxs2])

    # phpsessid 文本框更新机制
    php_textbox.change(lambda x: x, inputs=php_textbox, outputs=php_textbox2)
    php_textbox2.change(lambda x: x, inputs=php_textbox2, outputs=php_textbox)

demo.launch(theme=gr.themes.Soft(),
            pwa=False,
            share=False,
            inbrowser=True
            )  # share=True 会生成公网链接