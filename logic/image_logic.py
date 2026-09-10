# -*- coding: utf-8 -*-
"""
logic/image_logic.py — 图片 / 文件名的纯业务逻辑 + PID 屏蔽列表

从原 test_app.py「业务逻辑函数」一节拆出：
- get_image / filename_split / last_im_process
- pid_filter_add / skip_pid_filter（pids_filter.txt 读写）

pids_filter_list 为本模块级可变列表，供 workers / UI 共享
（通过「原地修改」保证各处看到同一份数据，行为与原全局变量一致）。

⚠️ 第一阶段仅做代码拆分，逻辑与原 test_app.py 保持一致。
"""

import os

from . import config_logic  # 先触发 config_logic 的启动初始化（目录/默认文件复制等）


# ==================== PID 屏蔽列表（全局共享可变列表） ====================
def _load_pids_filter_list():
    """读取 pids_filter.txt 内容到列表"""
    with open(config_logic.pids_filter_dir, 'a+') as f:
        f.seek(0)
        lines = f.read().splitlines()
        if lines == ['']:
            return []
        return lines


pids_filter_list = _load_pids_filter_list()


# ==================== 业务逻辑函数 ====================
def get_image(image_list, index):
    if 0 <= index < len(image_list):
        return image_list[index]
    return None


def filename_split(filename):
    for i in ['-', '_', '.', '/', '?', '!', '&']:
        filename = filename.split(i)[0]
    return filename


def last_im_process(image_list, index):
    if len(image_list) == 0:
        return -1
    if index < -1:
        return -1
    if index >= len(image_list):
        return len(image_list) - 1
    if index == len(image_list) - 1:
        return -1
    return index


def pid_filter_add(pid, add_filter):
    global pids_filter_list
    if pid is None:
        return
    if add_filter and pid not in pids_filter_list:
        pids_filter_list.append(pid)
        with open(config_logic.pids_filter_dir, 'w') as f:
            for p in pids_filter_list:
                f.write(str(p) + '\n')


def skip_pid_filter(image_list, index):
    for i in range(index + 1, len(image_list)):
        pid = filename_split(os.path.basename(image_list[i]))
        if pid not in pids_filter_list:
            return i
    return -1
