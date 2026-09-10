# -*- coding: utf-8 -*-
"""
workers/save_worker.py — 保存单张原图的后台任务

从原 test_app.py 拆出：SaveWorker

⚠️ 第一阶段仅做代码拆分，逻辑与原 test_app.py 保持一致。
"""

import os
import pathlib

from PySide6.QtCore import QObject, Signal, Slot

from pixiv_image_download import link_to_image
from pixiv_imagelink import link_find

from logic import config_logic


class SaveWorker(QObject):
    finished = Signal()
    error = Signal(str)
    exists = Signal(str)  # 文件已存在

    def __init__(self, save_subdir, php, image_index, pid):
        super().__init__()
        self.save_subdir = save_subdir
        self.php = php
        self.image_index = image_index
        self.pid = pid

    @Slot()
    def run(self):
        try:
            os.makedirs(self.save_subdir, exist_ok=True)
            pid_links = link_find(self.php, self.pid)
            idx = int(self.image_index) if self.image_index is not None else 0
            page_url = pid_links['links'][idx + 1]['original']
            page_name = page_url.split('/')[-1]

            # 递归检查 saved/ 下所有子目录是否有同名文件
            found = False
            for f in pathlib.Path(config_logic.save_dir).rglob(page_name):
                if f.is_file():
                    found = True
                    break
            if found:
                self.exists.emit(page_name)
                return

            link_to_image(self.save_subdir, page_name, page_url, self.php)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
