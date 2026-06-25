import sys
import os
import time
import random
import json
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QPushButton, QGroupBox, QScrollArea,
    QMessageBox, QComboBox, QGridLayout, QTextEdit, QStackedWidget, QFileDialog
)
from PySide6.QtGui import QPixmap, QFont, QIcon, QWheelEvent, QMouseEvent, QShortcut, QKeySequence
from PySide6.QtCore import Qt, QThread, QObject, Signal, Slot, QTimer, QEvent, QPoint

import shutil
import pathlib
import pixiv_id
from pixiv_image_download import link_to_image, filename_extract_index
from pixiv_imagelink import link_find
import get_phpsessid as gps
import requests
from model_script.function import predict_onnx as model_predict

# ==================== 初始化变量 ====================
MIN_WAIT_SECONDS = 0.1
MAX_WAIT_SECONDS = 0.3


def resource_path(relative_path):
    """获取打包后资源文件的路径（兼容 PyInstaller，只读）"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def data_path(relative_path):
    """获取可写数据文件的路径（当前工作目录，用于运行时修改的文件）"""
    return os.path.join(os.path.abspath("."), relative_path)


def _find_default_image():
    """从 theme/default_image/ 查找第一张可用图片作为默认"""
    exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
    for base in [resource_path('theme/default_image'),
                 os.path.join(os.path.abspath("."), 'theme', 'default_image')]:
        if os.path.isdir(base):
            for f in sorted(os.listdir(base)):
                if f.lower().endswith(exts):
                    return os.path.join(base, f)
    return resource_path('143035291_p0.jpg')


default_image = _find_default_image()
pids_filter_dir = data_path('pids_filter.txt')
phpsessid_file = data_path('phpsessid.txt')
temp_dir = 'temp'
save_dir = 'saved'
model_path = os.path.join(os.path.abspath("."), 'models', 'nahida_cnn_best.onnx')

# 确保 models 目录存在
model_dir = os.path.join(os.path.abspath("."), 'models')
os.makedirs(model_dir, exist_ok=True)

# 配置文件路径
config_dir = os.path.join(os.path.abspath("."), 'config')
config_file = os.path.join(config_dir, 'config.json')

# 读取 pids_filter.txt（优先当前目录，不存在则从打包目录复制默认文件）
if not os.path.exists(pids_filter_dir):
    src = resource_path('pids_filter.txt')
    if os.path.exists(src):
        shutil.copy2(src, pids_filter_dir)

with open(pids_filter_dir, 'a+') as f:
    f.seek(0)
    pids_filter_list = f.read().splitlines()
    if pids_filter_list == ['']:
        pids_filter_list = []

# 读取 phpsessid.txt（优先当前目录，不存在则从打包目录复制默认文件）
if not os.path.exists(phpsessid_file):
    src = resource_path('phpsessid.txt')
    if os.path.exists(src):
        shutil.copy2(src, phpsessid_file)

with open(phpsessid_file, 'a+') as f:
    f.seek(0)
    phpsessid = f.readline().rstrip()

os.makedirs(save_dir, exist_ok=True)
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.makedirs(temp_dir, exist_ok=True)


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
        with open(pids_filter_dir, 'w') as f:
            for p in pids_filter_list:
                f.write(str(p) + '\n')


def skip_pid_filter(image_list, index):
    for i in range(index + 1, len(image_list)):
        pid = filename_split(os.path.basename(image_list[i]))
        if pid not in pids_filter_list:
            return i
    return -1


def check_pixiv(php_id):
    try:
        response = requests.get(
            "https://www.pixiv.net/ajax/user/extra",
            cookies={"PHPSESSID": php_id},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if response.status_code == 200:
            return True, "✅ 连接成功"
        else:
            return False, f"❌ 连接失败，状态码: {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "❌ 连接超时"
    except Exception as e:
        return False, f"❌ 连接失败: {e}"


# ==================== Worker 线程（使用QObject + moveToThread方式） ====================
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
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)

            sub_dir = os.path.join(temp_dir, self.content)
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
            for f in pathlib.Path(save_dir).rglob(page_name):
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


class GetPHPSESSIDWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    @Slot()
    def run(self):
        try:
            php = gps.get_phpsessid()
            self.finished.emit(php)
        except Exception as e:
            self.error.emit(str(e))


class CheckPHPSESSIDWorker(QObject):
    finished = Signal(bool, str)  # (success, message)

    def __init__(self, php):
        super().__init__()
        self.php = php

    @Slot()
    def run(self):
        try:
            success, msg = check_pixiv(self.php)
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, f"检测异常: {e}")


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
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)

            result = []
            self.log(f"正在获取作者 {self.author_id} 的作品列表...")

            user_data = pixiv_id.user_works_id(self.author_id, self.php)
            pid_list = user_data['WorkIds']
            user_name = user_data.get('UserName')
            if not user_name:
                user_name = str(self.author_id)
            self.log(f"作者: {user_name}, 共 {len(pid_list)} 个作品")

            sub_dir = os.path.join(temp_dir, user_name)
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


# ==================== PyQt应用类 ====================
class PixivFilterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pixiv 图片筛选器")
        self._set_app_icon()
        self.setGeometry(100, 100, 1200, 750)

        self.current_index = 0
        self.current_index2 = 0
        self.current_index3 = 0
        
        # 初始化线程变量
        self.search_worker = None
        self.search_thread = None
        self.search_worker2 = None
        self.search_thread2 = None
        self.search_worker3 = None
        self.search_thread3 = None
        self.save_worker = None
        self.save_thread = None
        self.save_worker2 = None
        self.save_thread2 = None
        self.save_worker3 = None
        self.save_thread3 = None
        self._save_pid = None
        self._save_pid2 = None
        self._save_pid3 = None
        # 暂停状态
        self._search_paused = False
        self._search_paused2 = False
        self._search_paused3 = False

        # 保存线程池（允许并发保存）
        self._save_threads3 = []

        # 每个Tab独立的图片列表
        self.image_list_tab1 = []
        self.image_list_tab2 = []
        self.image_list_tab3 = []

        # 每个Tab独立的默认图片
        self.default_image_tab1 = default_image
        self.default_image_tab2 = default_image
        self.default_image_tab3 = default_image

        # 从配置文件加载上次保存的设置
        self._load_config()

        # 自定义侧边栏（水平文字）+ 堆栈面板
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        sidebar = QWidget()
        sidebar.setFixedWidth(130)
        sidebar.setStyleSheet("background-color: #2c2c2c;")
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(0)

        self.tab_btn1 = QPushButton("  ☰  筛选器")
        self.tab_btn1.setFixedHeight(45)
        self.tab_btn1.setStyleSheet("""
            QPushButton { text-align: left; padding: 8px 15px; border: none; 
                          color: white; font-size: 13px; background: #3c3c3c; }
            QPushButton:hover { background: #4a4a4a; }
        """)
        self.tab_btn1.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        self.tab_btn2 = QPushButton("  ☆  纳西妲")
        self.tab_btn2.setFixedHeight(45)
        self.tab_btn2.setStyleSheet("""
            QPushButton { text-align: left; padding: 8px 15px; border: none;
                          color: white; font-size: 13px; background: #2c2c2c; }
            QPushButton:hover { background: #4a4a4a; }
        """)
        self.tab_btn2.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        self.tab_btn3 = QPushButton("  👤  作者作品")
        self.tab_btn3.setFixedHeight(45)
        self.tab_btn3.setStyleSheet("""
            QPushButton { text-align: left; padding: 8px 15px; border: none;
                          color: white; font-size: 13px; background: #2c2c2c; }
            QPushButton:hover { background: #4a4a4a; }
        """)
        self.tab_btn3.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        self.tab_btn4 = QPushButton("  ⚙  设置")
        self.tab_btn4.setFixedHeight(45)
        self.tab_btn4.setStyleSheet("""
            QPushButton { text-align: left; padding: 8px 15px; border: none;
                          color: white; font-size: 13px; background: #2c2c2c; }
            QPushButton:hover { background: #4a4a4a; }
        """)
        self.tab_btn4.clicked.connect(lambda: self.stack.setCurrentIndex(3))

        sidebar_layout.addWidget(self.tab_btn1)
        sidebar_layout.addWidget(self.tab_btn2)
        sidebar_layout.addWidget(self.tab_btn3)
        sidebar_layout.addWidget(self.tab_btn4)
        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)

        # 堆栈面板
        self.stack = QStackedWidget()
        self.tab1 = self.create_filter_tab()
        self.tab2 = self.create_special_filter_tab()
        self.tab3 = self.create_author_tab()
        self.tab4 = self.create_settings_tab()
        self.stack.addWidget(self.tab1)
        self.stack.addWidget(self.tab2)
        self.stack.addWidget(self.tab3)
        self.stack.addWidget(self.tab4)
        self.stack.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack, 1)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 缩放状态（初始化必须在 image_label 创建之后）
        self._zoom1 = 0
        self._zoom2 = 0
        self._zoom3 = 0
        self._pixmap1 = None
        self._pixmap2 = None
        self._pixmap3 = None
        self.image_label.installEventFilter(self)
        self.image_label2.installEventFilter(self)
        self.image_label3.installEventFilter(self)
        # 滚动区域的视口也要安装事件过滤，因为滚轮事件可能被视口拦截
        self.scroll_area.viewport().installEventFilter(self)
        self.scroll_area2.viewport().installEventFilter(self)
        self.scroll_area3.viewport().installEventFilter(self)

        # 延迟到窗口显示后再加载默认图片，确保视口尺寸正确（自适应）
        QTimer.singleShot(0, self.update_image_display)

        # 拖拽状态
        self._drag_pos = None

        # 全局快捷键：左右方向键映射到上下一张
        self._shortcut_left = QShortcut(QKeySequence(Qt.Key_Left), self)
        self._shortcut_left.activated.connect(self._on_shortcut_prev)
        self._shortcut_right = QShortcut(QKeySequence(Qt.Key_Right), self)
        self._shortcut_right.activated.connect(self._on_shortcut_next)

    # ==================== 配置读写 ====================
    def _load_config(self):
        """从 config/config.json 加载上次保存的设置，不存在则创建默认配置"""
        if not os.path.exists(config_file):
            self._save_config()
            return
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            tab1 = data.get('default_image_tab1', '')
            tab2 = data.get('default_image_tab2', '')
            tab3 = data.get('default_image_tab3', '')
            if tab1 == '' or (tab1 and os.path.exists(tab1)):
                self.default_image_tab1 = tab1
            if tab2 == '' or (tab2 and os.path.exists(tab2)):
                self.default_image_tab2 = tab2
            if tab3 == '' or (tab3 and os.path.exists(tab3)):
                self.default_image_tab3 = tab3
        except Exception as e:
            print(f"读取配置文件失败: {e}")

    def _save_config(self):
        """保存当前设置到 config/config.json"""
        os.makedirs(config_dir, exist_ok=True)
        try:
            data = {
                'default_image_tab1': self.default_image_tab1,
                'default_image_tab2': self.default_image_tab2,
                'default_image_tab3': self.default_image_tab3,
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def eventFilter(self, obj, event):
        # 滚轮缩放
        if event.type() == QEvent.Type.Wheel:
            if obj is self.image_label or obj is self.scroll_area.viewport():
                self._on_wheel(event, 1)
                return True
            elif obj is self.image_label2 or obj is self.scroll_area2.viewport():
                self._on_wheel(event, 2)
                return True
            elif obj is self.image_label3 or obj is self.scroll_area3.viewport():
                self._on_wheel(event, 3)
                return True

        # 鼠标拖拽移动图片
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            if obj in (self.image_label, self.scroll_area.viewport()):
                label, scroll = self.image_label, self.scroll_area
            elif obj in (self.image_label2, self.scroll_area2.viewport()):
                label, scroll = self.image_label2, self.scroll_area2
            elif obj in (self.image_label3, self.scroll_area3.viewport()):
                label, scroll = self.image_label3, self.scroll_area3
            else:
                label = None
            if label:
                scroll.setCursor(Qt.CursorShape.ClosedHandCursor)
                self._drag_pos = event.globalPosition().toPoint()
                return True

        if event.type() == QEvent.Type.MouseMove and self._drag_pos is not None:
            if obj in (self.image_label, self.scroll_area.viewport()):
                label, scroll = self.image_label, self.scroll_area
            elif obj in (self.image_label2, self.scroll_area2.viewport()):
                label, scroll = self.image_label2, self.scroll_area2
            elif obj in (self.image_label3, self.scroll_area3.viewport()):
                label, scroll = self.image_label3, self.scroll_area3
            else:
                label = None
            if label:
                delta = event.globalPosition().toPoint() - self._drag_pos
                self._drag_pos = event.globalPosition().toPoint()
                h_bar = scroll.horizontalScrollBar()
                v_bar = scroll.verticalScrollBar()
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
                return True

        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if obj in (self.image_label, self.scroll_area.viewport()):
                    self.scroll_area.setCursor(Qt.CursorShape.ArrowCursor)
                elif obj in (self.image_label2, self.scroll_area2.viewport()):
                    self.scroll_area2.setCursor(Qt.CursorShape.ArrowCursor)
                return True

        return super().eventFilter(obj, event)

    def create_filter_tab(self):
        widget = QWidget()
        main_layout = QVBoxLayout()

        search_group = QGroupBox("搜索参数")
        search_layout = QGridLayout()

        search_layout.addWidget(QLabel("搜索关键词:"), 0, 0)
        self.keywords_input = QLineEdit()
        search_layout.addWidget(self.keywords_input, 0, 1)

        search_layout.addWidget(QLabel("内容过滤:"), 1, 0)
        filter_row = QHBoxLayout()
        filter_row.setAlignment(Qt.AlignLeft)
        self.r18_checkbox = QCheckBox("R18过滤")
        self.r18_checkbox.setChecked(True)
        filter_row.addWidget(self.r18_checkbox)

        self.r18g_checkbox = QCheckBox("R18G过滤")
        self.r18g_checkbox.setChecked(True)
        filter_row.addWidget(self.r18g_checkbox)

        self.r18_only_checkbox = QCheckBox("仅R18内容")
        filter_row.addWidget(self.r18_only_checkbox)
        search_layout.addLayout(filter_row, 1, 1, 1, 3)

        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)

        # R18 互斥逻辑（冲突时禁用）
        def _update_r18_state():
            r18_any = self.r18_checkbox.isChecked() or self.r18g_checkbox.isChecked()
            r18_only = self.r18_only_checkbox.isChecked()
            self.r18_checkbox.setEnabled(not r18_only)
            self.r18g_checkbox.setEnabled(not r18_only)
            self.r18_only_checkbox.setEnabled(not r18_any)
        self.r18_checkbox.stateChanged.connect(_update_r18_state)
        self.r18g_checkbox.stateChanged.connect(_update_r18_state)
        self.r18_only_checkbox.stateChanged.connect(_update_r18_state)
        _update_r18_state()

        content_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        # 图片显示容器（滚动拖动 + 文件名叠加层）
        self.image_container = QWidget()
        self.image_container.setMinimumSize(600, 500)
        container_layout = QGridLayout(self.image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("border: 1px solid gray;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        container_layout.addWidget(self.scroll_area, 0, 0)

        self.filename_label = QLabel()
        self.filename_label.setStyleSheet("""
            background-color: rgba(0,0,0,150);
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
        """)
        self.filename_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.filename_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        container_layout.addWidget(self.filename_label, 0, 0, Qt.AlignRight | Qt.AlignTop)

        left_layout.addWidget(self.image_container)

        right_layout = QVBoxLayout()
        pid_filter_group = QGroupBox("选项")
        pid_layout = QVBoxLayout()
        self.pid_filter_checkbox = QCheckBox("pid屏蔽")
        pid_layout.addWidget(self.pid_filter_checkbox)

        self.model_identify_checkbox1 = QCheckBox("模型识别")
        pid_layout.addWidget(self.model_identify_checkbox1)

        pid_layout.addWidget(QLabel("下载方式:"))
        self.dl_mode_combo1 = QComboBox()
        self.dl_mode_combo1.addItems(["页数模式", "图片张数", "PID个数"])
        pid_layout.addWidget(self.dl_mode_combo1)
        self.dl_spin1 = QSpinBox()
        self.dl_spin1.setMinimum(1)
        self.dl_spin1.setMaximum(20)
        self.dl_spin1.setValue(1)
        pid_layout.addWidget(self.dl_spin1)
        def _update_dl_spin1():
            m = self.dl_mode_combo1.currentText()
            self.dl_spin1.setMaximum(20 if m == "页数模式" else 100)
            self.dl_spin1.setValue(1)
        self.dl_mode_combo1.currentIndexChanged.connect(_update_dl_spin1)

        pid_filter_group.setLayout(pid_layout)
        right_layout.addWidget(pid_filter_group)

        info_group = QGroupBox("下载信息")
        info_layout = QVBoxLayout()
        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setMaximumHeight(150)
        info_layout.addWidget(self.info_box)
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setStyleSheet("background-color: #dc3545; color: white;")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setVisible(False)
        info_layout.addWidget(self.stop_btn)
        info_group.setLayout(info_layout)
        right_layout.addWidget(info_group)
        right_layout.addStretch()

        content_layout.addLayout(left_layout, 5)
        content_layout.addLayout(right_layout, 1)
        main_layout.addLayout(content_layout)

        button_layout = QHBoxLayout()
        self.search_btn = QPushButton("🔍 搜索")
        self.search_btn.setStyleSheet("background-color: #0084ff; color: white;")
        self.search_btn.clicked.connect(self.on_search_clicked)
        button_layout.addWidget(self.search_btn)

        self.prev_btn = QPushButton("⬅ 上一张")
        self.prev_btn.setStyleSheet("background-color: #6c757d; color: white;")
        self.prev_btn.clicked.connect(self.on_prev_clicked)
        button_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("下一张 ➡")
        self.next_btn.setStyleSheet("background-color: #6c757d; color: white;")
        self.next_btn.clicked.connect(self.on_next_clicked)
        button_layout.addWidget(self.next_btn)

        self.save_btn = QPushButton("✅ 保存")
        self.save_btn.setStyleSheet("background-color: #28a745; color: white;")
        self.save_btn.clicked.connect(self.on_save_clicked)
        button_layout.addWidget(self.save_btn)

        main_layout.addLayout(button_layout)
        widget.setLayout(main_layout)
        return widget

    def create_special_filter_tab(self):
        widget = QWidget()
        main_layout = QVBoxLayout()

        content_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        # 图片显示容器（滚动拖动 + 文件名叠加层）
        self.image_container2 = QWidget()
        self.image_container2.setMinimumSize(600, 500)
        container_layout2 = QGridLayout(self.image_container2)
        container_layout2.setContentsMargins(0, 0, 0, 0)

        self.scroll_area2 = QScrollArea()
        self.scroll_area2.setWidgetResizable(False)
        self.scroll_area2.setAlignment(Qt.AlignCenter)
        self.scroll_area2.setStyleSheet("border: 1px solid gray;")
        self.scroll_area2.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area2.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.image_label2 = QLabel()
        self.image_label2.setAlignment(Qt.AlignCenter)
        self.scroll_area2.setWidget(self.image_label2)
        container_layout2.addWidget(self.scroll_area2, 0, 0)

        self.filename_label2 = QLabel()
        self.filename_label2.setStyleSheet("""
            background-color: rgba(0,0,0,150);
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
        """)
        self.filename_label2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.filename_label2.setAttribute(Qt.WA_TransparentForMouseEvents)
        container_layout2.addWidget(self.filename_label2, 0, 0, Qt.AlignRight | Qt.AlignTop)

        left_layout.addWidget(self.image_container2)

        right_layout = QVBoxLayout()

        search_content_group = QGroupBox("搜索设置")
        search_content_layout = QVBoxLayout()
        search_content_layout.addWidget(QLabel("搜索内容:"))
        self.search_box2 = QComboBox()
        self.search_box2.addItems(['nahida', '纳西妲', 'ナヒーダ'])
        search_content_layout.addWidget(self.search_box2)
        search_content_group.setLayout(search_content_layout)
        right_layout.addWidget(search_content_group)

        filter_group = QGroupBox("选项")
        filter_layout = QVBoxLayout()

        filter_layout.addWidget(QLabel("过滤选项:"))
        self.pid_filter_checkbox2 = QCheckBox("pid屏蔽")
        filter_layout.addWidget(self.pid_filter_checkbox2)

        self.r18_checkbox2 = QCheckBox("R18过滤")
        self.r18_checkbox2.setChecked(True)
        filter_layout.addWidget(self.r18_checkbox2)

        self.r18g_checkbox2 = QCheckBox("R18G过滤")
        self.r18g_checkbox2.setChecked(True)
        filter_layout.addWidget(self.r18g_checkbox2)

        self.r18_only_checkbox2 = QCheckBox("仅R18内容")
        filter_layout.addWidget(self.r18_only_checkbox2)

        # R18 互斥逻辑（冲突时禁用）
        def _update_r18_state2():
            r18_any = self.r18_checkbox2.isChecked() or self.r18g_checkbox2.isChecked()
            r18_only = self.r18_only_checkbox2.isChecked()
            self.r18_checkbox2.setEnabled(not r18_only)
            self.r18g_checkbox2.setEnabled(not r18_only)
            self.r18_only_checkbox2.setEnabled(not r18_any)
        self.r18_checkbox2.stateChanged.connect(_update_r18_state2)
        self.r18g_checkbox2.stateChanged.connect(_update_r18_state2)
        self.r18_only_checkbox2.stateChanged.connect(_update_r18_state2)
        _update_r18_state2()

        filter_layout.addWidget(QLabel("下载方式:"))
        self.dl_mode_combo2 = QComboBox()
        self.dl_mode_combo2.addItems(["页数模式", "图片张数", "PID个数"])
        filter_layout.addWidget(self.dl_mode_combo2)
        self.dl_spin2 = QSpinBox()
        self.dl_spin2.setMinimum(1)
        self.dl_spin2.setMaximum(20)
        self.dl_spin2.setValue(1)
        filter_layout.addWidget(self.dl_spin2)
        def _update_dl_spin2():
            m = self.dl_mode_combo2.currentText()
            self.dl_spin2.setMaximum(20 if m == "页数模式" else 100)
            self.dl_spin2.setValue(1)
        self.dl_mode_combo2.currentIndexChanged.connect(_update_dl_spin2)

        self.model_identify_checkbox2 = QCheckBox("模型识别")
        filter_layout.addWidget(self.model_identify_checkbox2)

        filter_group.setLayout(filter_layout)
        right_layout.addWidget(filter_group)

        info_group2 = QGroupBox("下载信息")
        info_layout2 = QVBoxLayout()
        self.info_box2 = QTextEdit()
        self.info_box2.setReadOnly(True)
        self.info_box2.setMaximumHeight(150)
        info_layout2.addWidget(self.info_box2)
        self.stop_btn2 = QPushButton("⏹ 停止")
        self.stop_btn2.setStyleSheet("background-color: #dc3545; color: white;")
        self.stop_btn2.clicked.connect(self._on_stop_clicked2)
        self.stop_btn2.setVisible(False)
        info_layout2.addWidget(self.stop_btn2)
        info_group2.setLayout(info_layout2)
        right_layout.addWidget(info_group2)

        right_layout.addStretch()

        content_layout.addLayout(left_layout, 5)
        content_layout.addLayout(right_layout, 1)
        main_layout.addLayout(content_layout)

        button_layout = QHBoxLayout()

        self.search_btn2 = QPushButton("🔍 搜索")
        self.search_btn2.setStyleSheet("background-color: #0084ff; color: white;")
        self.search_btn2.clicked.connect(self.on_search_clicked2)
        button_layout.addWidget(self.search_btn2)

        self.prev_btn2 = QPushButton("⬅ 上一张")
        self.prev_btn2.setStyleSheet("background-color: #6c757d; color: white;")
        self.prev_btn2.clicked.connect(self.on_prev_clicked2)
        button_layout.addWidget(self.prev_btn2)

        self.next_btn2 = QPushButton("下一张 ➡")
        self.next_btn2.setStyleSheet("background-color: #6c757d; color: white;")
        self.next_btn2.clicked.connect(self.on_next_clicked2)
        button_layout.addWidget(self.next_btn2)

        self.save_btn2 = QPushButton("✅ 保存")
        self.save_btn2.setStyleSheet("background-color: #28a745; color: white;")
        self.save_btn2.clicked.connect(self.on_save_clicked2)
        button_layout.addWidget(self.save_btn2)

        main_layout.addLayout(button_layout)
        widget.setLayout(main_layout)
        return widget

    # ==================== Tab3：作者作品 ====================
    def create_author_tab(self):
        """按作者ID搜索并展示作品"""
        widget = QWidget()
        main_layout = QVBoxLayout()

        search_group = QGroupBox("搜索参数")
        search_layout = QGridLayout()

        search_layout.addWidget(QLabel("作者ID:"), 0, 0)
        self.author_id_input = QLineEdit()
        search_layout.addWidget(self.author_id_input, 0, 1)

        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)

        content_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        self.image_container3 = QWidget()
        self.image_container3.setMinimumSize(600, 500)
        container_layout3 = QGridLayout(self.image_container3)
        container_layout3.setContentsMargins(0, 0, 0, 0)

        self.scroll_area3 = QScrollArea()
        self.scroll_area3.setWidgetResizable(False)
        self.scroll_area3.setAlignment(Qt.AlignCenter)
        self.scroll_area3.setStyleSheet("border: 1px solid gray;")
        self.scroll_area3.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area3.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.image_label3 = QLabel()
        self.image_label3.setAlignment(Qt.AlignCenter)
        self.scroll_area3.setWidget(self.image_label3)
        container_layout3.addWidget(self.scroll_area3, 0, 0)

        self.filename_label3 = QLabel()
        self.filename_label3.setStyleSheet("""
            background-color: rgba(0,0,0,150);
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
        """)
        self.filename_label3.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.filename_label3.setAttribute(Qt.WA_TransparentForMouseEvents)
        container_layout3.addWidget(self.filename_label3, 0, 0, Qt.AlignRight | Qt.AlignTop)

        left_layout.addWidget(self.image_container3)

        right_layout = QVBoxLayout()
        option_group = QGroupBox("选项")
        option_layout = QVBoxLayout()
        self.pid_filter_checkbox3 = QCheckBox("pid屏蔽")
        option_layout.addWidget(self.pid_filter_checkbox3)

        self.r18_checkbox3 = QCheckBox("R18过滤")
        self.r18_checkbox3.setChecked(True)
        option_layout.addWidget(self.r18_checkbox3)

        self.r18g_checkbox3 = QCheckBox("R18G过滤")
        self.r18g_checkbox3.setChecked(True)
        option_layout.addWidget(self.r18g_checkbox3)

        self.r18_only_checkbox3 = QCheckBox("仅R18内容")
        option_layout.addWidget(self.r18_only_checkbox3)

        # R18 互斥逻辑
        def _update_r18_state3():
            r18_any = self.r18_checkbox3.isChecked() or self.r18g_checkbox3.isChecked()
            r18_only = self.r18_only_checkbox3.isChecked()
            self.r18_checkbox3.setEnabled(not r18_only)
            self.r18g_checkbox3.setEnabled(not r18_only)
            self.r18_only_checkbox3.setEnabled(not r18_any)
        self.r18_checkbox3.stateChanged.connect(_update_r18_state3)
        self.r18g_checkbox3.stateChanged.connect(_update_r18_state3)
        self.r18_only_checkbox3.stateChanged.connect(_update_r18_state3)
        _update_r18_state3()

        self.model_identify_checkbox3 = QCheckBox("模型识别")
        option_layout.addWidget(self.model_identify_checkbox3)

        option_group.setLayout(option_layout)
        right_layout.addWidget(option_group)

        info_group3 = QGroupBox("下载信息")
        info_layout3 = QVBoxLayout()
        self.info_box3 = QTextEdit()
        self.info_box3.setReadOnly(True)
        self.info_box3.setMaximumHeight(150)
        info_layout3.addWidget(self.info_box3)
        self.stop_btn3 = QPushButton("⏹ 停止")
        self.stop_btn3.setStyleSheet("background-color: #dc3545; color: white;")
        self.stop_btn3.clicked.connect(self._on_stop_clicked3)
        self.stop_btn3.setVisible(False)
        info_layout3.addWidget(self.stop_btn3)
        info_group3.setLayout(info_layout3)
        right_layout.addWidget(info_group3)
        right_layout.addStretch()

        content_layout.addLayout(left_layout, 5)
        content_layout.addLayout(right_layout, 1)
        main_layout.addLayout(content_layout)

        button_layout = QHBoxLayout()
        self.search_btn3 = QPushButton("🔍 搜索")
        self.search_btn3.setStyleSheet("background-color: #0084ff; color: white;")
        self.search_btn3.clicked.connect(self.on_search_clicked3)
        button_layout.addWidget(self.search_btn3)

        self.prev_btn3 = QPushButton("⬅ 上一张")
        self.prev_btn3.setStyleSheet("background-color: #6c757d; color: white;")
        self.prev_btn3.clicked.connect(self.on_prev_clicked3)
        button_layout.addWidget(self.prev_btn3)

        self.next_btn3 = QPushButton("下一张 ➡")
        self.next_btn3.setStyleSheet("background-color: #6c757d; color: white;")
        self.next_btn3.clicked.connect(self.on_next_clicked3)
        button_layout.addWidget(self.next_btn3)

        self.save_btn3 = QPushButton("✅ 保存")
        self.save_btn3.setStyleSheet("background-color: #28a745; color: white;")
        self.save_btn3.clicked.connect(self.on_save_clicked3)
        button_layout.addWidget(self.save_btn3)

        main_layout.addLayout(button_layout)
        widget.setLayout(main_layout)
        return widget

    def create_settings_tab(self):
        """设置页面"""
        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("⚙ 设置")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # PHPSESSID 设置
        group = QGroupBox("PHPSESSID")
        group_layout = QVBoxLayout()

        php_row = QHBoxLayout()
        php_row.addWidget(QLabel("PHPSESSID:"))
        self.php_input_global = QLineEdit()
        self.php_input_global.setText(phpsessid)
        php_row.addWidget(self.php_input_global, 1)
        self.php_input_global.textChanged.connect(self._on_php_input_changed)

        self.get_php_btn = QPushButton("获取")
        self.get_php_btn.clicked.connect(self._on_get_phpsessid)
        php_row.addWidget(self.get_php_btn)

        self.check_php_btn = QPushButton("检测")
        self.check_php_btn.clicked.connect(self._on_check_phpsessid)
        php_row.addWidget(self.check_php_btn)

        group_layout.addLayout(php_row)

        self.php_status_label = QLabel("")
        self.php_status_label.setStyleSheet("padding: 4px;")
        group_layout.addWidget(self.php_status_label)

        group.setLayout(group_layout)
        layout.addWidget(group)

        # 模型路径设置
        model_group = QGroupBox("模型设置")
        model_layout = QVBoxLayout()

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("模型选择(ONNX):"))
        self.model_combo = QComboBox()
        model_row.addWidget(self.model_combo, 1)

        self.browse_model_btn = QPushButton("浏览目录")
        self.browse_model_btn.clicked.connect(self._on_browse_model_dir)
        model_row.addWidget(self.browse_model_btn)

        model_layout.addLayout(model_row)

        self.model_status_label = QLabel("")
        self.model_status_label.setStyleSheet("padding: 4px; color: gray;")
        model_layout.addWidget(self.model_status_label)

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # PID内张数限制设置
        page_limit_group = QGroupBox("下载过滤")
        page_limit_layout = QVBoxLayout()

        page_limit_row = QHBoxLayout()
        self.page_limit_checkbox = QCheckBox("PID内超过")
        self.page_limit_checkbox.toggled.connect(self._on_page_limit_toggled)
        page_limit_row.addWidget(self.page_limit_checkbox)

        self.page_limit_spin = QSpinBox()
        self.page_limit_spin.setMinimum(1)
        self.page_limit_spin.setMaximum(100)
        self.page_limit_spin.setValue(20)
        self.page_limit_spin.setEnabled(False)
        page_limit_row.addWidget(self.page_limit_spin)

        page_limit_row.addWidget(QLabel("张则跳过该PID"))
        page_limit_layout.addLayout(page_limit_row)

        page_limit_group.setLayout(page_limit_layout)
        layout.addWidget(page_limit_group)

        # 默认图片设置
        default_img_group = QGroupBox("默认图片设置")
        default_img_layout = QVBoxLayout()

        # 选择 Tab
        tab_row = QHBoxLayout()
        tab_row.addWidget(QLabel("选择 Tab:"))
        self.default_tab_combo = QComboBox()
        self.default_tab_combo.addItems(["筛选器", "纳西妲", "作者作品"])
        self.default_tab_combo.currentIndexChanged.connect(self._on_default_tab_changed)
        tab_row.addWidget(self.default_tab_combo, 1)
        default_img_layout.addLayout(tab_row)

        # 选择默认图片
        img_row = QHBoxLayout()
        img_row.addWidget(QLabel("默认图片:"))
        self.default_img_combo = QComboBox()
        self.default_img_combo.setMinimumWidth(200)
        img_row.addWidget(self.default_img_combo, 1)
        self.browse_default_img_btn = QPushButton("添加")
        self.browse_default_img_btn.clicked.connect(self._on_browse_default_image)
        img_row.addWidget(self.browse_default_img_btn)
        default_img_layout.addLayout(img_row)

        self.default_img_status = QLabel("")
        self.default_img_status.setStyleSheet("padding: 4px; color: gray;")
        default_img_layout.addWidget(self.default_img_status)

        default_img_group.setLayout(default_img_layout)
        layout.addWidget(default_img_group)

        # 初始扫描默认 models/ 目录
        self._scan_model_dir(os.path.join(os.path.abspath("."), 'models'))
        self.model_combo.currentIndexChanged.connect(self._on_model_selected)

        # 初始扫描默认图片
        self._scan_default_images()
        self.default_img_combo.currentIndexChanged.connect(self._on_default_image_selected)
        # 显示初始状态
        self._on_default_tab_changed(self.default_tab_combo.currentIndex())

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _on_php_input_changed(self):
        """用户手动修改 PHPSESSID 时恢复获取按钮"""
        self.get_php_btn.setEnabled(True)

    def _on_get_phpsessid(self):
        """获取 PHPSESSID（调用 get_phpsessid.py）"""
        self.get_php_btn.setEnabled(False)
        self.get_php_btn.setText("获取中...")
        self.php_status_label.setText("正在打开浏览器登录 Pixiv...")
        self.php_status_label.setStyleSheet("color: blue; padding: 4px;")

        # 用线程执行，避免阻塞UI
        self._php_worker = GetPHPSESSIDWorker()
        self._php_thread = QThread()
        self._php_worker.moveToThread(self._php_thread)
        self._php_worker.finished.connect(self._on_php_got)
        self._php_worker.error.connect(self._on_php_error)
        self._php_thread.started.connect(self._php_worker.run)
        self._php_worker.finished.connect(self._php_thread.quit)
        self._php_worker.error.connect(self._php_thread.quit)
        self._php_thread.start()

    def _on_php_got(self, php_value):
        self.php_input_global.setText(php_value)
        self.get_php_btn.setEnabled(True)
        self.get_php_btn.setText("获取")
        # 获取成功后自动检测
        self._on_check_phpsessid()

    def _on_php_error(self, msg):
        self.get_php_btn.setEnabled(True)
        self.get_php_btn.setText("获取")
        self.php_status_label.setText(f"❌ 获取失败: {msg}")
        self.php_status_label.setStyleSheet("color: red; padding: 4px;")

    def _on_check_phpsessid(self):
        """检测 PHPSESSID 是否有效（异步，不阻塞 UI）"""
        php = self.php_input_global.text().strip()
        if not php:
            self.php_status_label.setText("❌ PHPSESSID 为空")
            self.php_status_label.setStyleSheet("color: red; padding: 4px;")
            return

        self.check_php_btn.setEnabled(False)
        self.check_php_btn.setText("检测中...")
        self.php_status_label.setText("检测中...")
        self.php_status_label.setStyleSheet("color: blue; padding: 4px;")

        # 线程执行，避免阻塞 UI
        self._check_worker = CheckPHPSESSIDWorker(php)
        self._check_thread = QThread()
        self._check_worker.moveToThread(self._check_thread)
        self._check_worker.finished.connect(self._on_check_result)
        self._check_thread.started.connect(self._check_worker.run)
        self._check_worker.finished.connect(self._check_thread.quit)
        self._check_thread.start()

    def _on_check_result(self, success, msg):
        """检测完成回调"""
        self.check_php_btn.setEnabled(True)
        self.check_php_btn.setText("检测")
        self.php_status_label.setText(msg)
        self.php_status_label.setStyleSheet("color: green; padding: 4px;" if success else "color: red; padding: 4px;")

        php = self.php_input_global.text().strip()
        if success:
            with open(phpsessid_file, 'w') as f:
                f.write(php)
            self.get_php_btn.setEnabled(False)
            self.php_status_label.setText("✅ 已保存到 phpsessid.txt")
        else:
            self.get_php_btn.setEnabled(True)

    def _on_browse_model_dir(self):
        """浏览并选择模型目录，扫描其中的模型文件"""
        default_dir = os.path.join(os.path.abspath("."), 'models')
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择模型目录", default_dir
        )
        if dir_path:
            self._scan_model_dir(dir_path)

    def _scan_model_dir(self, directory):
        """扫描指定目录下的所有 .onnx 文件，填充下拉列表"""
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        if os.path.isdir(directory):
            model_files = [f for f in os.listdir(directory) if f.endswith('.onnx')]
            if model_files:
                for f in sorted(model_files):
                    full_path = os.path.join(directory, f)
                    self.model_combo.addItem(full_path, full_path)
                self.model_combo.setCurrentIndex(0)
                self._on_model_selected()
            else:
                self.model_status_label.setText("⚠️ 该目录下没有 .onnx 模型文件")
                self.model_status_label.setStyleSheet("color: orange; padding: 4px;")
                self.model_identify_checkbox1.setEnabled(False)
                self.model_identify_checkbox2.setEnabled(False)
                self.model_identify_checkbox1.setChecked(False)
                self.model_identify_checkbox2.setChecked(False)
        else:
            self.model_status_label.setText("⚠️ 目录不存在")
            self.model_status_label.setStyleSheet("color: orange; padding: 4px;")
        self.model_combo.blockSignals(False)

    def _on_model_selected(self):
        """下拉列表选择变更时更新全局模型路径"""
        global model_path
        path = self.model_combo.currentData()
        if path and os.path.exists(path):
            model_path = path
            self.model_status_label.setText(f"✅ 模型已加载: {os.path.basename(path)}")
            self.model_status_label.setStyleSheet("color: green; padding: 4px;")
            self.model_identify_checkbox1.setEnabled(True)
            self.model_identify_checkbox2.setEnabled(True)
            self.model_identify_checkbox3.setEnabled(True)
        else:
            self.model_status_label.setText("⚠️ ONNX 模型文件不存在")
            self.model_status_label.setStyleSheet("color: orange; padding: 4px;")
            self.model_identify_checkbox1.setEnabled(False)
            self.model_identify_checkbox2.setEnabled(False)
            self.model_identify_checkbox3.setEnabled(False)
            self.model_identify_checkbox1.setChecked(False)
            self.model_identify_checkbox2.setChecked(False)
            self.model_identify_checkbox3.setChecked(False)

    def _on_page_limit_toggled(self, checked):
        """PID张数限制复选框切换时联动 spinbox"""
        self.page_limit_spin.setEnabled(checked)

    # ==================== 默认图片设置 ====================
    def _scan_default_images(self):
        """扫描 theme/default_image 目录下的图片文件，填充下拉列表"""
        self.default_img_combo.blockSignals(True)
        self.default_img_combo.clear()

        exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
        image_entries = []
        seen = set()

        # 扫描 theme/default_image/ 和 theme/added_image/（同名文件后者覆盖前者）
        dirs = [
            ('default', os.path.join(os.path.abspath("."), 'theme', 'default_image')),
            ('added', os.path.join(os.path.abspath("."), 'theme', 'added_image')),
        ]

        for tag, d in dirs:
            if os.path.isdir(d):
                for f in sorted(os.listdir(d)):
                    if f.lower().endswith(exts) and os.path.isfile(os.path.join(d, f)):
                        path = os.path.abspath(os.path.join(d, f))
                        key = f.lower()
                        if key not in seen:
                            image_entries.append((f, path, tag))
                            seen.add(key)
                        else:
                            for i, (name, p, t) in enumerate(image_entries):
                                if name.lower() == key:
                                    image_entries[i] = (f, path, tag)
                                    break

        # 分开排序：预设在前，added在后，各自按文件名排序
        default_entries = sorted([e for e in image_entries if e[2] == 'default'], key=lambda x: x[0].lower())
        added_entries = sorted([e for e in image_entries if e[2] == 'added'], key=lambda x: x[0].lower())

        if image_entries:
            for fname, path, tag in default_entries + added_entries:
                if tag == 'default':
                    name_no_ext = os.path.splitext(fname)[0]
                    display = f"预设{name_no_ext}"
                else:
                    rel = os.path.relpath(path, os.path.abspath("."))
                    display = f"{fname} ({rel})"
                self.default_img_combo.addItem(display, path)
        else:
            self.default_img_combo.addItem("（未找到图片文件）", "")

        # 在最前面插入"无"选项
        self.default_img_combo.insertItem(0, "无", "")
        self._sync_default_img_combo()
        self.default_img_combo.blockSignals(False)

    def _sync_default_img_combo(self):
        """同步下拉列表显示当前 tab 已保存的默认图片"""
        tab_idx = self.default_tab_combo.currentIndex()
        if tab_idx == 0:
            current_default = self.default_image_tab1
        elif tab_idx == 1:
            current_default = self.default_image_tab2
        else:
            current_default = self.default_image_tab3
        if current_default == "":
            self.default_img_combo.setCurrentIndex(0)  # 选中"无"
        elif current_default:
            idx = self.default_img_combo.findData(current_default)
            if idx < 0:
                idx = self.default_img_combo.findText(os.path.basename(current_default), Qt.MatchFlag.MatchContains)
            if idx >= 0:
                self.default_img_combo.setCurrentIndex(idx)

    def _on_default_tab_changed(self, index):
        """切换 Tab 选择时，显示对应的默认图片"""
        self._sync_default_img_combo()
        if index == 0:
            current = self.default_image_tab1
        elif index == 1:
            current = self.default_image_tab2
        else:
            current = self.default_image_tab3
        # 尝试用下拉框显示文字
        idx = self.default_img_combo.findData(current)
        display = self.default_img_combo.itemText(idx) if idx >= 0 else os.path.basename(current)
        self.default_img_status.setText(f"当前: {display}")

    def _on_default_image_selected(self, index):
        """从下拉列表选择默认图片时，保存到对应的 tab"""
        if index < 0:
            return
        img_path = self.default_img_combo.currentData()
        if not img_path and img_path != "":
            return
        if img_path and not os.path.exists(img_path):
            return

        display_name = self.default_img_combo.currentText()
        tab_idx = self.default_tab_combo.currentIndex()
        if tab_idx == 0:
            self.default_image_tab1 = img_path
            label = self.image_label
            self._zoom1 = 0
        elif tab_idx == 1:
            self.default_image_tab2 = img_path
            label = self.image_label2
            self._zoom2 = 0
        else:
            self.default_image_tab3 = img_path
            label = self.image_label3
            self._zoom3 = 0

        self._save_config()
        self.default_img_status.setText(f"✅ 已设置: {display_name}")
        self.default_img_status.setStyleSheet("padding: 4px; color: green;")

        # 刷新对应 tab 的展示框
        self._zoom = 0
        self.update_image_display(label=label)

    def _on_browse_default_image(self):
        """浏览并选择一张图片，复制到 theme/added_image 并设为默认图片"""
        added_dir = os.path.join(os.path.abspath("."), 'theme', 'added_image')
        os.makedirs(added_dir, exist_ok=True)
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择默认图片", added_dir,
            "图片文件 (*.jpg *.jpeg *.png *.gif *.webp *.bmp);;所有文件 (*)"
        )
        if file_path:
            # 复制到 theme/added_image/
            import shutil
            fname = os.path.basename(file_path)
            dest_path = os.path.join(added_dir, fname)
            if os.path.abspath(file_path) != os.path.abspath(dest_path):
                shutil.copy2(file_path, dest_path)

            # 刷新下拉列表并选中新添加的图片
            self._scan_default_images()
            idx = self.default_img_combo.findData(dest_path)
            if idx >= 0:
                self.default_img_combo.setCurrentIndex(idx)

            tab_idx = self.default_tab_combo.currentIndex()
            if tab_idx == 0:
                self.default_image_tab1 = dest_path
            else:
                self.default_image_tab2 = dest_path

            self._save_config()
            self.default_img_status.setText(f"✅ 已添加: {fname}")
            self.default_img_status.setStyleSheet("padding: 4px; color: green;")

    # ==================== Tab3 搜索 ====================
    def _set_buttons_enabled3(self, enabled):
        """统一控制Tab3按钮启用/禁用"""
        self.search_btn3.setEnabled(enabled)
        self.save_btn3.setEnabled(enabled)
        self.prev_btn3.setEnabled(enabled)
        self.next_btn3.setEnabled(enabled)

    def on_search_clicked3(self):
        """按作者ID搜索"""
        if self.search_thread3 and self.search_thread3.isRunning():
            if self.search_worker3 and self.search_worker3.stop_event.is_set():
                self.search_thread3.quit()
                self.search_thread3.wait(500)
                if self.search_thread3.isRunning():
                    self.search_thread3.terminate()
                    self.search_thread3.wait()
                self.search_worker3 = None
                self.search_thread3 = None
                self.search_btn3.setText("🔍 搜索")
                self._search_paused3 = False
                self.stop_btn3.setVisible(False)
            elif self._search_paused3:
                self.search_worker3.pause_event.clear()
                self._search_paused3 = False
                self.search_btn3.setText("⏸ 暂停")
                self.info_box3.append("▶ 继续下载")
            else:
                self.search_worker3.pause_event.set()
                self._search_paused3 = True
                self.search_btn3.setText("▶ 继续")
                self.info_box3.append("⏸ 已暂停")
            return

        # 正常启动搜索
        author_id = self.author_id_input.text().strip()
        if not author_id:
            QMessageBox.warning(self, "警告", "请输入作者ID")
            return

        php = self.php_input_global.text()
        self.php_session = php

        self.image_list_tab3.clear()
        self.image_label3.setPixmap(QPixmap())
        self.image_label3.setText("搜索中...")
        self.image_label3.repaint()
        QApplication.processEvents()
        self.info_box3.clear()

        self.search_btn3.setEnabled(True)
        self.search_btn3.setText("搜索中...")
        self.save_btn3.setEnabled(False)
        self.prev_btn3.setEnabled(False)
        self.next_btn3.setEnabled(False)
        self.stop_btn3.setVisible(True)
        self._search_paused3 = False

        r18_rem = 0 if self.r18_checkbox3.isChecked() else 1
        r18g_rem = 0 if self.r18g_checkbox3.isChecked() else 1
        r18_only = self.r18_only_checkbox3.isChecked()

        # 使用 AuthorSearchWorker
        self.search_worker3 = AuthorSearchWorker(
            author_id, php,
            r18_rem=r18_rem, r18g_rem=r18g_rem, r18_only=r18_only,
            model_identify=self.model_identify_checkbox3.isChecked(),
            model_path=model_path,
        )
        self.search_thread3 = QThread()
        self.search_worker3.moveToThread(self.search_thread3)

        self.search_worker3.finished.connect(self._on_search_done3)
        self.search_worker3.image_ready.connect(self._on_image_ready3)
        self.search_worker3.log_msg.connect(self.info_box3.append)
        self.search_worker3.error.connect(self._on_search_error3)
        self.search_thread3.started.connect(self.search_worker3.run)
        self.search_worker3.finished.connect(self.search_thread3.quit)
        self.search_worker3.error.connect(self.search_thread3.quit)

        self.search_thread3.start()

    def _on_search_done3(self, result, user_name):
        self.search_btn3.setEnabled(True)
        self.search_btn3.setText("🔍 搜索")
        self._search_paused3 = False
        self.stop_btn3.setVisible(False)
        self._author_name = user_name

        count = len(self.image_list_tab3)
        if count == 0:
            QMessageBox.information(self, "提示", "没有找到符合条件的图片")
        else:
            self.show_toast(f"✅ 下载完毕！共 {count} 张图片", "success", 3000)

    def _on_image_ready3(self, path):
        self.image_list_tab3.append(path)
        if len(self.image_list_tab3) == 1:
            self.current_index3 = 0
            self.update_image_display(0, self.image_label3)
            self.save_btn3.setEnabled(True)
            self.prev_btn3.setEnabled(True)
            self.next_btn3.setEnabled(True)

    def _on_search_error3(self, msg):
        self.search_btn3.setEnabled(True)
        self.search_btn3.setText("🔍 搜索")
        self._search_paused3 = False
        self.save_btn3.setEnabled(False)
        self.prev_btn3.setEnabled(False)
        self.next_btn3.setEnabled(False)
        self.stop_btn3.setVisible(False)
        self.info_box3.append(f"❌ 搜索失败: {msg}")

    def _on_stop_clicked3(self):
        if self.search_worker3:
            self.search_worker3.stop_event.set()
        self.search_btn3.setText("🔍 搜索")
        self._search_paused3 = False
        self.stop_btn3.setVisible(False)
        self.info_box3.append("⏹ 已停止搜索")

    # ==================== Tab3 导航 ====================
    def on_prev_clicked3(self):
        if not self.image_list_tab3:
            return
        if self.current_index3 > 0:
            self.current_index3 -= 1
            self.update_image_display(self.current_index3, self.image_label3)
            self._update_save_btn_state(self.image_list_tab3, self.current_index3, self.save_btn3)
        else:
            self.show_toast("已经是第一张啦~", "warning", 1500)

    def on_next_clicked3(self):
        if not self.image_list_tab3:
            return
        if self.current_index3 < len(self.image_list_tab3) - 1:
            self.current_index3 += 1
            self.update_image_display(self.current_index3, self.image_label3)
            self._update_save_btn_state(self.image_list_tab3, self.current_index3, self.save_btn3)
        else:
            self.show_toast("已经是最后一张啦~", "warning", 1500)

    def _on_tab_changed(self, index):
        """切换标签时更新侧边栏按钮样式"""
        active = """
            QPushButton { text-align: left; padding: 8px 15px; border: none;
                          color: white; font-size: 13px; background: #3c3c3c; }
            QPushButton:hover { background: #4a4a4a; }
        """
        inactive = """
            QPushButton { text-align: left; padding: 8px 15px; border: none;
                          color: white; font-size: 13px; background: #2c2c2c; }
            QPushButton:hover { background: #4a4a4a; }
        """
        self.tab_btn1.setStyleSheet(active if index == 0 else inactive)
        self.tab_btn2.setStyleSheet(active if index == 1 else inactive)
        self.tab_btn3.setStyleSheet(active if index == 2 else inactive)
        self.tab_btn4.setStyleSheet(active if index == 3 else inactive)

        # 切换到对应的 tab 时重新自适应展示
        if index == 0 and self._pixmap1 is None:
            QTimer.singleShot(0, self.update_image_display)
        elif index == 0 and self._pixmap1 is not None:
            QTimer.singleShot(0, lambda: self._apply_zoom(self.image_label, self._zoom1))
        elif index == 1 and self._pixmap2 is None:
            QTimer.singleShot(0, lambda: self.update_image_display(label=self.image_label2))
        elif index == 1 and self._pixmap2 is not None:
            QTimer.singleShot(0, lambda: self._apply_zoom(self.image_label2, self._zoom2))
        elif index == 2 and self._pixmap3 is None:
            QTimer.singleShot(0, lambda: self.update_image_display(label=self.image_label3))
        elif index == 2 and self._pixmap3 is not None:
            QTimer.singleShot(0, lambda: self._apply_zoom(self.image_label3, self._zoom3))

    def _set_app_icon(self):
        """设置窗口图标（使用 pixiv.ico）"""
        ico_path = resource_path("pixiv.ico")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))

    def update_image_display(self, index=None, label=None):
        if label is None:
            label = self.image_label

        if label is self.image_label:
            il = self.image_list_tab1
            filename_lbl = self.filename_label
        elif label is self.image_label2:
            il = self.image_list_tab2
            filename_lbl = self.filename_label2
        else:
            il = self.image_list_tab3
            filename_lbl = self.filename_label3

        if index is None:
            if label is self.image_label:
                image_path = self.default_image_tab1
            elif label is self.image_label2:
                image_path = self.default_image_tab2
            else:
                image_path = self.default_image_tab3
            filename_lbl.clear()
        else:
            image_path = get_image(il, index)
            if image_path is None:
                label.setText("没有更多图片")
                return

        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if label is self.image_label:
                self._pixmap1 = pixmap
                zoom = self._zoom1
            elif label is self.image_label2:
                self._pixmap2 = pixmap
                zoom = self._zoom2
            else:
                self._pixmap3 = pixmap
                zoom = self._zoom3
            self._apply_zoom(label, zoom)
            fname = os.path.basename(image_path)
            pid = filename_split(fname)
            idx = filename_extract_index(fname)
            display_name = f"{pid}_p{idx}" if idx else pid
            filename_lbl.setText(display_name)
        else:
            label.setText(f"图片不存在: {image_path}")
            filename_lbl.clear()

    def _apply_zoom(self, label, zoom):
        """按缩放因子显示图片，保持宽高比不拉伸"""
        if label is self.image_label:
            pixmap = self._pixmap1
            scroll = self.scroll_area
        elif label is self.image_label2:
            pixmap = self._pixmap2
            scroll = self.scroll_area2
        else:
            pixmap = self._pixmap3
            scroll = self.scroll_area3
        if pixmap is None or pixmap.isNull():
            return
        # 获取滚动区域视口尺寸（图片实际可显示区域）
        cw = max(scroll.viewport().width() - 5, 10)
        ch = max(scroll.viewport().height() - 5, 10)
        if zoom == 0:
            scaled = pixmap.scaled(cw, ch, Qt.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            fit_w = cw
            fit_h = int(pixmap.height() * cw / pixmap.width())
            w = max(int(fit_w * zoom), 10)
            h = max(int(fit_h * zoom), 10)
            scaled = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(scaled)
        # 更新标签自身尺寸为缩放后的图片尺寸（滚动区域据此决定是否显示滚动条）
        label.resize(scaled.size())

    def _on_wheel(self, event, tab):
        """滚轮缩放"""
        zoom = self._zoom1 if tab == 1 else (self._zoom2 if tab == 2 else self._zoom3)
        if zoom == 0:
            zoom = 1.0
        if event.angleDelta().y() > 0:
            zoom *= 1.2
        else:
            zoom *= 1 / 1.2
        zoom = max(0.1, min(zoom, 10.0))
        if tab == 1:
            self._zoom1 = zoom
            label = self.image_label
        elif tab == 2:
            self._zoom2 = zoom
            label = self.image_label2
        else:
            self._zoom3 = zoom
            label = self.image_label3
        self._apply_zoom(label, zoom)

    def resizeEvent(self, event):
        """窗口缩放时重绘图片"""
        super().resizeEvent(event)
        if hasattr(self, 'image_label') and self._pixmap1:
            self._apply_zoom(self.image_label, self._zoom1)
        if hasattr(self, 'image_label2') and self._pixmap2:
            self._apply_zoom(self.image_label2, self._zoom2)
        if hasattr(self, 'image_label3') and self._pixmap3:
            self._apply_zoom(self.image_label3, self._zoom3)

    def _set_buttons_enabled(self, enabled, tab=1):
        """统一控制按钮启用/禁用（不影响搜索按钮文字）"""
        if tab == 1:
            self.search_btn.setEnabled(enabled)
            self.save_btn.setEnabled(enabled)
            self.prev_btn.setEnabled(enabled)
            self.next_btn.setEnabled(enabled)
            self.model_identify_checkbox1.setEnabled(enabled)
        else:
            self.search_btn2.setEnabled(enabled)
            self.save_btn2.setEnabled(enabled)
            self.prev_btn2.setEnabled(enabled)
            self.next_btn2.setEnabled(enabled)
            self.model_identify_checkbox2.setEnabled(enabled)

    # ==================== Tab1 搜索 ====================
    def on_search_clicked(self):
        # 已有 worker 在运行 → 暂停/继续切换
        if self.search_thread and self.search_thread.isRunning():
            # 如果已发送停止信号，不进入暂停逻辑，直接允许重新搜索
            if self.search_worker and self.search_worker.stop_event.is_set():
                self.search_thread.quit()
                self.search_thread.wait(500)
                if self.search_thread.isRunning():
                    self.search_thread.terminate()
                    self.search_thread.wait()
                self.search_worker = None
                self.search_thread = None
                self.search_btn.setText("🔍 搜索")
                self._search_paused = False
                self.stop_btn.setVisible(False)
            elif self._search_paused:
                # 继续下载
                self.search_worker.pause_event.clear()
                self._search_paused = False
                self.search_btn.setText("⏸ 暂停")
                self.info_box.append("▶ 继续下载")
            else:
                # 暂停下载
                self.search_worker.pause_event.set()
                self._search_paused = True
                self.search_btn.setText("▶ 继续")
                self.info_box.append("⏸ 已暂停")
            return

        # 没有在跑 → 正常启动搜索
        content = self.keywords_input.text().strip()
        if not content:
            QMessageBox.warning(self, "警告", "请输入搜索关键词")
            return

        php = self.php_input_global.text()
        self.php_session = php

        self.image_list_tab1.clear()
        # 清除图像显示：设置空白 pixmap 避免闪旧图
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("搜索中...")
        self.image_label.repaint()
        QApplication.processEvents()
        self.info_box.clear()

        r18_rem = 0 if self.r18_checkbox.isChecked() else 1
        r18g_rem = 0 if self.r18g_checkbox.isChecked() else 1
        r18_only = self.r18_only_checkbox.isChecked()

        # 搜索按钮保持可用（可点击暂停），其他按钮等第一张图到了再启用
        self.search_btn.setEnabled(True)
        self.search_btn.setText("搜索中...")
        self.save_btn.setEnabled(False)
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.model_identify_checkbox1.setEnabled(False)
        self.stop_btn.setVisible(True)
        self._search_paused = False

        # 解析下载方式
        dl_mode1 = self.dl_mode_combo1.currentText()
        if dl_mode1 == "页数模式":
            dl_pages1 = self.dl_spin1.value()
            dl_limit1 = 0
            dl_limit_mode1 = "图片张数"
        else:
            dl_pages1 = 20
            dl_limit1 = self.dl_spin1.value()
            dl_limit_mode1 = dl_mode1

        # 使用QThread + moveToThread方式处理耗时操作
        self.search_worker = SearchWorker(
            content, php, r18_rem, r18g_rem, dl_pages1,
            download_limit=dl_limit1,
            limit_mode=dl_limit_mode1,
            model_identify=self.model_identify_checkbox1.isChecked(),
            model_path=model_path,
            page_limit_enabled=self.page_limit_checkbox.isChecked(),
            page_limit=self.page_limit_spin.value(),
            r18_only=r18_only
        )
        self.search_thread = QThread()
        self.search_worker.moveToThread(self.search_thread)
        
        self.search_worker.finished.connect(self._on_search_done)
        self.search_worker.image_ready.connect(self._on_image_ready)
        self.search_worker.log_msg.connect(self.info_box.append)
        self.search_worker.error.connect(self._on_search_error)
        self.search_thread.started.connect(self.search_worker.run)
        self.search_worker.finished.connect(self.search_thread.quit)
        self.search_worker.error.connect(self.search_thread.quit)
        
        self.search_thread.start()

    def _on_stop_clicked(self):
        """停止 Tab1 搜索"""
        if self.search_worker:
            self.search_worker.stop_event.set()
        self.search_btn.setText("🔍 搜索")
        self._search_paused = False
        self.stop_btn.setVisible(False)
        self.info_box.append("⏹ 已停止搜索")

    def _on_search_done(self, result):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 搜索")
        self._search_paused = False
        self.model_identify_checkbox1.setEnabled(True)
        self.stop_btn.setVisible(False)

        if not self.image_list_tab1:
            QMessageBox.information(self, "提示", "没有找到符合条件的图片")
            self.update_image_display()
        else:
            # 已通过 image_ready 实时添加，这里只需启用按钮
            pass

    def _on_image_ready(self, path):
        """每下载完一张图立即更新展示"""
        self.image_list_tab1.append(path)
        if len(self.image_list_tab1) == 1:
            self.current_index = 0
            self.update_image_display(0)
            # 第一张图到了就启用操作按钮，搜索按钮保持禁用
            self.save_btn.setEnabled(True)
            self.prev_btn.setEnabled(True)
            self.next_btn.setEnabled(True)

    def _on_search_error(self, msg):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 搜索")
        self._search_paused = False
        self.save_btn.setEnabled(False)
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.model_identify_checkbox1.setEnabled(True)
        self.stop_btn.setVisible(False)
        self.info_box.append(f"❌ 搜索失败: {msg}")

    # ==================== Tab2 搜索 ====================
    def on_search_clicked2(self):
        # 已有 worker 在运行 → 暂停/继续切换
        if self.search_thread2 and self.search_thread2.isRunning():
            # 如果已发送停止信号，不进入暂停逻辑，直接允许重新搜索
            if self.search_worker2 and self.search_worker2.stop_event.is_set():
                self.search_thread2.quit()
                self.search_thread2.wait(500)
                if self.search_thread2.isRunning():
                    self.search_thread2.terminate()
                    self.search_thread2.wait()
                self.search_worker2 = None
                self.search_thread2 = None
                self.search_btn2.setText("🔍 搜索")
                self._search_paused2 = False
                self.stop_btn2.setVisible(False)
            elif self._search_paused2:
                self.search_worker2.pause_event.clear()
                self._search_paused2 = False
                self.search_btn2.setText("⏸ 暂停")
                self.info_box2.append("▶ 继续下载")
            else:
                self.search_worker2.pause_event.set()
                self._search_paused2 = True
                self.search_btn2.setText("▶ 继续")
                self.info_box2.append("⏸ 已暂停")
            return

        # 正常启动搜索
        content = self.search_box2.currentText()
        php = self.php_input_global.text()
        self.php_session = php

        self.image_list_tab2.clear()
        # 清除图像显示：设置空白 pixmap 避免闪旧图
        self.image_label2.setPixmap(QPixmap())
        self.image_label2.setText("搜索中...")
        self.image_label2.repaint()
        QApplication.processEvents()
        self.info_box2.clear()

        r18_rem = 0 if self.r18_checkbox2.isChecked() else 1
        r18g_rem = 0 if self.r18g_checkbox2.isChecked() else 1
        r18_only = self.r18_only_checkbox2.isChecked()

        self.search_btn2.setEnabled(True)
        self.search_btn2.setText("搜索中...")
        self.save_btn2.setEnabled(False)
        self.prev_btn2.setEnabled(False)
        self.next_btn2.setEnabled(False)
        self.model_identify_checkbox2.setEnabled(False)
        self.stop_btn2.setVisible(True)
        self._search_paused2 = False

        # 解析下载方式
        dl_mode2 = self.dl_mode_combo2.currentText()
        if dl_mode2 == "页数模式":
            dl_pages2 = self.dl_spin2.value()
            dl_limit2 = 0
            dl_limit_mode2 = "图片张数"
        else:
            dl_pages2 = 20
            dl_limit2 = self.dl_spin2.value()
            dl_limit_mode2 = dl_mode2

        # 使用QThread + moveToThread方式处理耗时操作
        self.search_worker2 = SearchWorker(
            content, php, r18_rem, r18g_rem, dl_pages2,
            download_limit=dl_limit2,
            limit_mode=dl_limit_mode2,
            model_identify=self.model_identify_checkbox2.isChecked(),
            model_path=model_path,
            page_limit_enabled=self.page_limit_checkbox.isChecked(),
            page_limit=self.page_limit_spin.value(),
            r18_only=r18_only
        )
        self.search_thread2 = QThread()
        self.search_worker2.moveToThread(self.search_thread2)
        
        self.search_worker2.finished.connect(self._on_search_done2)
        self.search_worker2.image_ready.connect(self._on_image_ready2)
        self.search_worker2.log_msg.connect(self.info_box2.append)
        self.search_worker2.error.connect(self._on_search_error2)
        self.search_thread2.started.connect(self.search_worker2.run)
        self.search_worker2.finished.connect(self.search_thread2.quit)
        self.search_worker2.error.connect(self.search_thread2.quit)
        
        self.search_thread2.start()

    def _on_stop_clicked2(self):
        """停止 Tab2 搜索"""
        if self.search_worker2:
            self.search_worker2.stop_event.set()
        self.search_btn2.setText("🔍 搜索")
        self._search_paused2 = False
        self.stop_btn2.setVisible(False)
        self.info_box2.append("⏹ 已停止搜索")

    def _on_search_done2(self, result):
        self.search_btn2.setEnabled(True)
        self.search_btn2.setText("🔍 搜索")
        self._search_paused2 = False
        self.model_identify_checkbox2.setEnabled(True)
        self.stop_btn2.setVisible(False)

        if not self.image_list_tab2:
            QMessageBox.information(self, "提示", "没有找到符合条件的图片")
            self.update_image_display(label=self.image_label2)

    def _on_image_ready2(self, path):
        """每下载完一张图立即更新展示 (Tab2)"""
        self.image_list_tab2.append(path)
        if len(self.image_list_tab2) == 1:
            self.current_index2 = 0
            self.update_image_display(0, self.image_label2)
            self.save_btn2.setEnabled(True)
            self.prev_btn2.setEnabled(True)
            self.next_btn2.setEnabled(True)

    def _on_search_error2(self, msg):
        self.search_btn2.setEnabled(True)
        self.search_btn2.setText("🔍 搜索")
        self._search_paused2 = False
        self.save_btn2.setEnabled(False)
        self.prev_btn2.setEnabled(False)
        self.next_btn2.setEnabled(False)
        self.model_identify_checkbox2.setEnabled(True)
        self.stop_btn2.setVisible(False)
        self.info_box2.append(f"❌ 搜索失败: {msg}")

    # ==================== Tab1 保存 ====================
    def show_toast(self, message, toast_type="success", duration=2000):
        """显示一个浮窗提示，过一段时间自动消失（重复调用会替换上一个）"""
        # 删除上一个浮窗
        if hasattr(self, '_current_toast') and self._current_toast is not None:
            try:
                self._current_toast.deleteLater()
                self._current_toast = None
            except RuntimeError:
                pass

        color_map = {
            "success": "#28a745",
            "error": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8",
        }
        bg_color = color_map.get(toast_type, "#28a745")
        text_color = "#fff" if toast_type != "warning" else "#333"

        toast = QLabel(message, self)
        toast.setWordWrap(True)  # 文字过长时自动换行
        max_w = max(int(self.width() * 0.6), 200)  # 最大宽度为窗口宽度的60%，最少200px
        toast.setMaximumWidth(max_w)
        toast.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        toast.adjustSize()

        # 居中显示在窗口顶部
        x = (self.width() - toast.width()) // 2
        y = 20
        toast.move(x, y)
        toast.show()

        # 保存引用并定时消失
        self._current_toast = toast
        QTimer.singleShot(duration, lambda: self._clear_toast(toast))

    def _clear_toast(self, toast):
        """清除指定的浮窗（避免误删新浮窗）"""
        try:
            if hasattr(self, '_current_toast') and self._current_toast is toast:
                self._current_toast = None
            toast.deleteLater()
        except RuntimeError:
            pass

    # ==================== 统一保存方法（Tab1/Tab2/Tab3 共用） ====================
    def _do_save(self, save_subdir, btn, pid_attr, filter_checkbox):
        """统一的保存逻辑

        Args:
            save_subdir: 保存子目录 (saved/{关键词}/)
            btn: 对应的保存按钮 (save_btn / save_btn2 / save_btn3)
            pid_attr: 存储 pid 的属性名，如 '_save_pid'
            filter_checkbox: pid 屏蔽复选框
        """
        # 确定当前 tab 的图片列表和索引
        if btn is self.save_btn:
            img_list = self.image_list_tab1
            idx = self.current_index
            image_label = self.image_label
        elif btn is self.save_btn2:
            img_list = self.image_list_tab2
            idx = self.current_index2
            image_label = self.image_label2
        else:
            img_list = self.image_list_tab3
            idx = self.current_index3
            image_label = self.image_label3

        if not (0 <= idx < len(img_list)):
            QMessageBox.warning(self, "警告", "没有有效的图片可保存")
            return

        # Tab1 特殊：需要搜索关键词作为保存目录（已由调用方传入 save_subdir）
        # Tab3 特殊：需要作者名（已由调用方传入 save_subdir）

        img_path = img_list[idx]
        image_filename = os.path.basename(img_path)
        image_index = filename_extract_index(image_filename)
        save_pid = filename_split(image_filename)
        setattr(self, pid_attr, save_pid)
        php = self.php_input_global.text()

        # 标记此图片正在保存
        if not hasattr(self, '_saving_paths'):
            self._saving_paths = set()
        self._saving_paths.add(img_path)
        btn.setEnabled(False)
        btn.setText("保存中...")

        worker = SaveWorker(save_subdir, php, image_index, save_pid)
        thread = QThread()
        worker.moveToThread(thread)

        # 把回调参数存到 worker 上
        worker._btn = btn
        worker._filter_checkbox = filter_checkbox
        worker._pid_attr = pid_attr
        worker._img_path = img_path

        worker.finished.connect(self._on_save_common_done, Qt.QueuedConnection)
        worker.error.connect(self._on_save_common_error, Qt.QueuedConnection)
        worker.exists.connect(self._on_save_common_exists, Qt.QueuedConnection)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.exists.connect(thread.quit)

        # 保持引用防止 GC
        if not hasattr(self, '_save_threads'):
            self._save_threads = []
        self._save_threads.append((worker, thread))
        thread.start()

    def _update_save_btn_state(self, img_list, cur_idx, btn):
        """根据当前图片是否在保存中，更新按钮状态"""
        if img_list and 0 <= cur_idx < len(img_list):
            cur_path = img_list[cur_idx]
            if hasattr(self, '_saving_paths') and cur_path in self._saving_paths:
                btn.setEnabled(False)
                btn.setText("保存中...")
                return
        btn.setEnabled(True)
        btn.setText("✅ 保存")

    def _on_save_common_done(self):
        """保存成功通用回调"""
        worker = self.sender()
        self._saving_paths.discard(worker._img_path)
        if worker._filter_checkbox.isChecked():
            pid_filter_add(getattr(self, worker._pid_attr), True)
        self._update_btn_by_worker(worker)
        self.show_toast("✅ 保存成功", "success")

    def _on_save_common_error(self, msg):
        """保存失败通用回调"""
        worker = self.sender()
        self._saving_paths.discard(worker._img_path)
        self._update_btn_by_worker(worker)
        self.show_toast(f"❌ 保存失败: {msg}", "error", 3000)

    def _on_save_common_exists(self, name):
        """文件已存在通用回调"""
        worker = self.sender()
        self._saving_paths.discard(worker._img_path)
        self._update_btn_by_worker(worker)
        self.show_toast(f"⚠️ 文件已存在: {name}", "warning", 2500)

    def _update_btn_by_worker(self, worker):
        """根据 worker 对应的 tab 更新保存按钮状态"""
        if worker._btn is self.save_btn:
            self._update_save_btn_state(self.image_list_tab1, self.current_index, self.save_btn)
        elif worker._btn is self.save_btn2:
            self._update_save_btn_state(self.image_list_tab2, self.current_index2, self.save_btn2)
        else:
            self._update_save_btn_state(self.image_list_tab3, self.current_index3, self.save_btn3)

    def on_save_clicked(self):
        """Tab1 保存"""
        search_con = self.keywords_input.text().strip()
        if not search_con:
            QMessageBox.warning(self, "警告", "请先输入搜索关键词")
            return
        self._do_save(
            os.path.join(save_dir, search_con),
            self.save_btn, '_save_pid',
            self.pid_filter_checkbox
        )

    def on_save_clicked2(self):
        """Tab2 保存"""
        self._do_save(
            os.path.join(save_dir, '纳西妲'),
            self.save_btn2, '_save_pid2',
            self.pid_filter_checkbox2
        )

    def on_save_clicked3(self):
        """Tab3 保存"""
        author_subdir = getattr(self, '_author_name', None) or self.author_id_input.text().strip()
        self._do_save(
            os.path.join(save_dir, author_subdir),
            self.save_btn3, '_save_pid3',
            self.pid_filter_checkbox3
        )

    # ==================== 导航：上一张 / 下一张 ====================
    def on_prev_clicked(self):
        if not self.image_list_tab1:
            return
        if self.current_index > 0:
            self.current_index -= 1
            self.update_image_display(self.current_index)
            self._update_save_btn_state(self.image_list_tab1, self.current_index, self.save_btn)
        else:
            self.show_toast("已经是第一张啦~", "warning", 1500)

    def on_next_clicked(self):
        if not self.image_list_tab1:
            return
        if self.current_index < len(self.image_list_tab1) - 1:
            self.current_index += 1
            self.update_image_display(self.current_index)
            self._update_save_btn_state(self.image_list_tab1, self.current_index, self.save_btn)
        else:
            self.show_toast("已经是最后一张啦~", "warning", 1500)

    def on_prev_clicked2(self):
        if not self.image_list_tab2:
            return
        if self.current_index2 > 0:
            self.current_index2 -= 1
            self.update_image_display(self.current_index2, self.image_label2)
            self._update_save_btn_state(self.image_list_tab2, self.current_index2, self.save_btn2)
        else:
            self.show_toast("已是第一张", "warning", 1500)

    def on_next_clicked2(self):
        if not self.image_list_tab2:
            return
        if self.current_index2 < len(self.image_list_tab2) - 1:
            self.current_index2 += 1
            self.update_image_display(self.current_index2, self.image_label2)
            self._update_save_btn_state(self.image_list_tab2, self.current_index2, self.save_btn2)
        else:
            self.show_toast("已是最后一张", "warning", 1500)

    # ==================== 键盘快捷键 ====================
    def _on_shortcut_prev(self):
        """全局快捷键：← 上一张"""
        tab = self.stack.currentIndex()
        if tab == 0:
            self.on_prev_clicked()
        elif tab == 1:
            self.on_prev_clicked2()
        elif tab == 2:
            self.on_prev_clicked3()

    def _on_shortcut_next(self):
        """全局快捷键：→ 下一张"""
        tab = self.stack.currentIndex()
        if tab == 0:
            self.on_next_clicked()
        elif tab == 1:
            self.on_next_clicked2()
        elif tab == 2:
            self.on_next_clicked3()

    # ==================== 资源清理 ====================
    def closeEvent(self, event):
        """窗口关闭时清理线程"""
        # 先通知所有 worker 停止
        for worker in [self.search_worker, self.search_worker2, self.search_worker3]:
            if worker:
                worker.stop_event.set()
        
        # 清理所有运行中的线程
        threads_to_quit = [
            (self.search_thread, self.search_worker),
            (self.search_thread2, self.search_worker2),
            (self.search_thread3, self.search_worker3),
        ]
        
        for thread, worker in threads_to_quit:
            if thread and thread.isRunning():
                thread.quit()
                thread.wait(1000)
                if thread.isRunning():
                    thread.terminate()
                    thread.wait()

        # 清理保存线程池
        if hasattr(self, '_save_threads'):
            for worker, thread in self._save_threads:
                if thread and thread.isRunning():
                    thread.quit()
                    thread.wait(500)
                    if thread.isRunning():
                        thread.terminate()
                        thread.wait()
            self._save_threads.clear()
        
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PixivFilterApp()
    window.show()
    sys.exit(app.exec())