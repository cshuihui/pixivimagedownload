# -*- coding: utf-8 -*-
"""
workers/search_worker.py — 关键词/作者搜索并下载预览图的后台任务

从原 test_app.py 拆出：
- SearchWorker（关键词搜索下载，Tab1/Tab2 共用）
- AuthorSearchWorker（按作者 ID 搜索下载，Tab3 用）

⚠️ 第一阶段仅做代码拆分，逻辑与原 test_app.py 保持一致。
"""

import os
import shutil
import time
import random
import threading

from PySide6.QtCore import QObject, Signal, Slot

import pixiv_id
from pixiv_image_download import link_to_image
from pixiv_imagelink import link_find
from model_script.function import predict_onnx as model_predict

from logic import config_logic
from logic.image_logic import pids_filter_list

# ==================== 初始化变量 ====================
MIN_WAIT_SECONDS = 0.1
MAX_WAIT_SECONDS = 0.3


class SearchWorker(QObject):
    finished = Signal(list)
    image_ready = Signal(str)  # 每下载完一张立即发出信号
    log_msg = Signal(str)      # 下载信息输出
    error = Signal(str)

    def __init__(self, content, php, r18_rem, r18g_rem, pages, download_limit=0, limit_mode="图片张数",
                 model_identify=False, model_path="", page_limit_enabled=False, page_limit=5,
                 r18_only=False):
        super().__init__()
        self.content = content
        self.php = php
        self.r18_rem = r18_rem
        self.r18g_rem = r18g_rem
        self.r18_only = r18_only
        self.pages = pages
        self.download_limit = download_limit
        self.limit_mode = limit_mode  # "页数模式" / "图片张数" / "PID个数"
        self.model_identify = model_identify
        self.model_path = model_path
        self.page_limit_enabled = page_limit_enabled
        self.page_limit = page_limit
        self.pause_event = threading.Event()  # set=暂停, clear=继续
        self.stop_event = threading.Event()   # set=停止

    def check_pause(self):
        """检查暂停状态，暂停时阻塞直到恢复或收到停止信号"""
        while self.pause_event.is_set() and not self.stop_event.is_set():
            time.sleep(0.2)

    def _check_limit_reached(self, count):
        """检查是否达到下载限制，达到则打印提示并返回 True"""
        if self.download_limit > 0 and count >= self.download_limit:
            self.log(f"已达下载限制 ({self.download_limit} {self.limit_mode})，停止搜索")
            return True
        return False

    def log(self, msg):
        """同时输出到终端和UI信息框"""
        print(msg)
        self.log_msg.emit(msg)

    @Slot()
    def run(self):
        try:
            if os.path.exists(config_logic.temp_dir):
                shutil.rmtree(config_logic.temp_dir)
            os.makedirs(config_logic.temp_dir, exist_ok=True)

            sub_dir = os.path.join(config_logic.temp_dir, self.content)
            os.makedirs(sub_dir, exist_ok=True)

            result = []
            download_count = 0

            for page in range(1, self.pages + 1):
                if self.stop_event.is_set() or self._check_limit_reached(download_count):
                    break
                pid_list = pixiv_id.id_save(self.content, page, self.php, stop_event=self.stop_event)
                self.log(f"正在下载第 {page} 页的图片")
                time.sleep(random.randint(1, 3))
                for _index, pid in enumerate(pid_list, start=1):
                    if self.stop_event.is_set() or self._check_limit_reached(download_count):
                        break
                    self.check_pause()  # 每处理一个 PID 前检查暂停
                    if self.stop_event.is_set():
                        break
                    if pid in pids_filter_list:
                        self.log(f"{pid} 已过滤(用户选择)")
                        continue
                    # 获取作品信息（带重试）
                    pid_links = None
                    for retry in range(1, 6):
                        if self.stop_event.is_set():
                            break
                        try:
                            pid_links = link_find(self.php, pid)
                            break
                        except Exception as e:
                            wait = 5 * retry
                            self.log(f"{pid} 连接异常(第{retry}次)，{wait}秒后重试: {e}")
                            time.sleep(wait)
                    if pid_links is None:
                        self.log(f"{pid} 获取失败，跳过")
                        continue
                    if self.r18_only:
                        if pid_links['R18'] != 1:
                            self.log(f"{pid} 已过滤(非R18)")
                            continue
                    elif pid_links['R18'] != self.r18_rem or pid_links['R18G'] != self.r18g_rem:
                        self.log(f"{pid} 已过滤(r18/r18g类型)")
                        continue
                    # PID内张数超过限制则跳过
                    if self.page_limit_enabled and pid_links['pageCount'] > self.page_limit:
                        self.log(f"{pid} 共 {pid_links['pageCount']} 张，超过限制({self.page_limit}张)，跳过")
                        continue
                    self.log(f"正在下载 PID {pid} ({_index}/{len(pid_list)})，共 {pid_links['pageCount']} 张")
                    for pn in range(1, pid_links['pageCount'] + 1):
                        if self.stop_event.is_set():
                            break
                        if self.limit_mode == "图片张数" and self._check_limit_reached(download_count):
                            break
                        self.check_pause()  # 每张图下载前也检查
                        if self.stop_event.is_set():
                            break
                        page_url = pid_links['links'][pn]['regular']
                        page_name = page_url.split('/')[-1]
                        self.log(page_name)
                        # 下载图片（带重试）
                        dl_ok = False
                        for retry in range(1, 6):
                            if self.stop_event.is_set():
                                break
                            try:
                                if link_to_image(sub_dir, page_name, page_url, self.php):
                                    dl_ok = True
                                    break
                            except Exception as e:
                                wait = 5 * retry
                                self.log(f"  下载失败(第{retry}次)，{wait}秒后重试: {e}")
                                time.sleep(wait)
                        if not dl_ok:
                            self.log(f"  {page_name} 下载失败，跳过")
                            break
                        full_path = os.path.abspath(os.path.join(sub_dir, page_name))

                        # 模型识别：不是纳西妲则跳过
                        is_nahida = True  # 未启用识别或识别失败时默认保留
                        if self.model_identify and self.model_path and os.path.exists(self.model_path):
                            try:
                                pred_result = model_predict(self.model_path, full_path)
                                if pred_result == 1:
                                    self.log(f"  🧠 模型识别: 是纳西妲 (类别{pred_result})")
                                else:
                                    self.log(f"  🧠 模型识别: 不是纳西妲 (类别{pred_result})，跳过")
                                    is_nahida = False
                            except Exception as e:
                                self.log(f"  ⚠️ 模型识别失败: {e}")

                        if not is_nahida:
                            # 不加入结果列表，但保留temp中的文件
                            continue

                        result.append(full_path)
                        if self.limit_mode == "图片张数":
                            download_count += 1
                        self.image_ready.emit(full_path)  # 立即通知UI
                    # PID个数模式：每处理完一个PID计数+1
                    if self.limit_mode == "PID个数":
                        download_count += 1
                    self.log("下载完成！准备下载下一个…")
                    time.sleep(random.uniform(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS))

            if not self.stop_event.is_set():
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AuthorSearchWorker(QObject):
    """按作者ID搜索作品并下载预览图"""
    finished = Signal(list, str)  # (image_paths, user_name)
    image_ready = Signal(str)
    log_msg = Signal(str)
    error = Signal(str)

    def __init__(self, author_id, php, r18_rem=1, r18g_rem=1, r18_only=False,
                 model_identify=False, model_path=""):
        super().__init__()
        self.author_id = author_id
        self.php = php
        self.r18_rem = r18_rem
        self.r18g_rem = r18g_rem
        self.r18_only = r18_only
        self.model_identify = model_identify
        self.model_path = model_path
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

    def log(self, msg):
        print(msg)
        self.log_msg.emit(msg)

    def check_pause(self):
        """检查暂停状态，暂停时阻塞直到恢复或收到停止信号"""
        while self.pause_event.is_set() and not self.stop_event.is_set():
            time.sleep(0.2)

    @Slot()
    def run(self):
        try:
            if os.path.exists(config_logic.temp_dir):
                shutil.rmtree(config_logic.temp_dir)
            os.makedirs(config_logic.temp_dir, exist_ok=True)

            result = []
            self.log(f"正在获取作者 {self.author_id} 的作品列表...")

            user_data = pixiv_id.user_works_id(self.author_id, self.php)
            pid_list = user_data['WorkIds']
            user_name = user_data.get('UserName')
            if not user_name:
                user_name = str(self.author_id)
            self.log(f"作者: {user_name}, 共 {len(pid_list)} 个作品")

            sub_dir = os.path.join(config_logic.temp_dir, user_name)
            os.makedirs(sub_dir, exist_ok=True)

            for _index, pid in enumerate(pid_list, start=1):
                if self.stop_event.is_set():
                    break
                self.check_pause()
                if self.stop_event.is_set():
                    break

                pid_links = None
                for retry in range(1, 6):
                    if self.stop_event.is_set():
                        break
                    try:
                        pid_links = link_find(self.php, pid)
                        break
                    except Exception as e:
                        wait = 5 * retry
                        self.log(f"{pid} 连接异常(第{retry}次)，{wait}秒后重试: {e}")
                        time.sleep(wait)
                if pid_links is None:
                    self.log(f"{pid} 获取失败，跳过")
                    continue

                # R18 过滤
                if self.r18_only:
                    if pid_links['R18'] != 1:
                        self.log(f"{pid} 已过滤(非R18)")
                        continue
                elif pid_links['R18'] != self.r18_rem or pid_links['R18G'] != self.r18g_rem:
                    self.log(f"{pid} 已过滤(r18/r18g类型)")
                    continue

                self.log(f"正在下载 PID {pid} ({_index}/{len(pid_list)})，共 {pid_links['pageCount']} 张")
                for pn in range(1, pid_links['pageCount'] + 1):
                    if self.stop_event.is_set():
                        break
                    self.check_pause()
                    if self.stop_event.is_set():
                        break
                    page_url = pid_links['links'][pn]['regular']
                    page_name = page_url.split('/')[-1]
                    self.log(page_name)
                    dl_ok = False
                    for retry in range(1, 6):
                        if self.stop_event.is_set():
                            break
                        try:
                            if link_to_image(sub_dir, page_name, page_url, self.php):
                                dl_ok = True
                                break
                        except Exception as e:
                            wait = 5 * retry
                            self.log(f"  下载失败(第{retry}次)，{wait}秒后重试: {e}")
                            time.sleep(wait)
                    if not dl_ok:
                        self.log(f"  下载失败，跳过")
                        break
                    full_path = os.path.abspath(os.path.join(sub_dir, page_name))

                    # 模型识别
                    is_match = True
                    if self.model_identify and self.model_path and os.path.exists(self.model_path):
                        try:
                            pred_result = model_predict(self.model_path, full_path)
                            if pred_result == 1:
                                self.log(f"  🧠 模型识别: 匹配 (类别{pred_result})")
                            else:
                                self.log(f"  🧠 模型识别: 不匹配 (类别{pred_result})，跳过")
                                is_match = False
                        except Exception as e:
                            self.log(f"  ⚠️ 模型识别失败: {e}")

                    if not is_match:
                        continue

                    result.append(full_path)
                    self.image_ready.emit(full_path)

                time.sleep(random.uniform(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS))

            if not self.stop_event.is_set():
                self.finished.emit(result, user_name)
        except Exception as e:
            self.error.emit(str(e))
