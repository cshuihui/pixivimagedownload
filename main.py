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

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import PixivFilterApp


def main():
    app = QApplication(sys.argv)
    window = PixivFilterApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
