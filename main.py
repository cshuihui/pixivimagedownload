# -*- coding: utf-8 -*-
"""
main.py — Pixiv 图片筛选器入口

项目结构：
- ui/main_window.py   → PixivFilterApp 主窗口（UI 搭建 + 事件/信号槽）
- ui/app.qss          → 全局样式表
- workers/            → 搜索 / 保存 / PHPSESSID 后台任务
- logic/              → 图片业务逻辑与配置读写
- model_script/       → 模型推理（「模型识别」功能）

入口仅负责创建 QApplication 并启动 PixivFilterApp。
"""

import os
import sys

# 打包后（PyInstaller）先把工作目录切到 exe 所在目录。
#
# logic/config_logic.py 在 **被 import 时** 就用 os.path.abspath(".") 算好了
# models/ theme/ config/ saved/ temp/ 这些路径，所以这一步必须发生在
# import 它之前 —— 也就是本文件所有项目内 import 之前。
#
# 否则从开始菜单 / 任务栏 / 快捷方式（起始目录与 exe 不同）启动时，上述路径
# 会指向错误位置，表现为「模型识别失效、背景图空白、下载跑到别处」。
# 从源码直接运行时 sys.frozen 不存在，行为完全不变。
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(os.path.abspath(sys.executable)))

from PySide6.QtWidgets import QApplication

from ui.main_window import PixivFilterApp


def main():
    app = QApplication(sys.argv)
    window = PixivFilterApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
