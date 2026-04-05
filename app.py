import gradio as gr
import os
import shutil
from pixiv_image_download import image_download

# 👉 假设这是你爬取后的图片路径列表
image_list = []
image_list_len = 0
phpsessid = '78166549_0A7GK0qSiaLwsDnuyfOUqn4dCd7BlphJ'
temp_dir = 'temp'
save_dir = "saved"
os.makedirs(save_dir, exist_ok=True)


# 🌿 当前显示图片
def get_image(index):
    if index < len(image_list):
        return image_list[index]
    return None


# ✅ 保存图片
def save_image(index):
    if len(image_list) > index >= 0:
        img_path = image_list[index]
        shutil.copy(img_path, save_dir)

    index = last_im_process(index)

    return index + 1, get_image(index + 1)


# ❌ 丢弃图片
def discard_image(index):
    index = last_im_process(index)
    return index + 1, get_image(index + 1)

def search_image(content, r18_filter, r18g_filter, pages):
    if r18_filter:
        r18_rem = 0
    else:
        r18_rem = 1
    if r18g_filter:
        r18g_rem = 0
    else:
        r18g_rem = 1
    image_download(content, phpsessid, r18_rem, r18g_rem, save_dir=temp_dir, last_page=int(pages))

    im_list = os.listdir(os.path.join(temp_dir, content))
    for file in im_list:
        image_list.append(os.path.abspath(os.path.join(temp_dir, content, file)))

    return 0, get_image(0)

def last_im_process(index):

    if len(image_list) == 0:
        return -1

    if index < -1 or index >= len(image_list):
        return -1

    if index == len(image_list) - 1:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        # 重新创建
        os.makedirs(temp_dir, exist_ok=True)

        image_list.clear()

        return -1

    return index


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
            with gr.Row():
                R18_rem_check = gr.Checkbox(value=True, label='R18过滤')
                R18G_rem_check = gr.Checkbox(value=True, label='R18G过滤')
            search_btn = gr.Button("搜索", variant="primary")



            image = gr.Image(type="filepath", height=800)

            with gr.Row():
                save_btn = gr.Button("✅ 保存", variant="primary")
                discard_btn = gr.Button("❌ 丢弃", variant='stop')

            # 初始化
            if state != 0:
                demo.load(get_image, inputs=state, outputs=image)

            # 按钮逻辑
            save_btn.click(save_image, inputs=state, outputs=[state, image])
            discard_btn.click(discard_image, inputs=state, outputs=[state, image])
            search_btn.click(search_image, inputs=[key_words, R18_rem_check, R18G_rem_check, search_pages], outputs=[state, image])


demo.launch(theme=gr.themes.Soft(),
               share=False,
               inbrowser=True
               )  # share=True 会生成公网链接