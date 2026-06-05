import sys
import os
import time
import random
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QPushButton, QGroupBox, QScrollArea,
    QMessageBox, QComboBox, QGridLayout, QTextEdit, QStackedWidget, QFileDialog
)
from PySide6.QtGui import QPixmap, QFont, QIcon, QWheelEvent, QMouseEvent
from PySide6.QtCore import Qt, QThread, QObject, Signal, Slot, QTimer, QEvent, QPoint

import shutil
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


default_image = resource_path('143035291_p0.jpg')
pids_filter_dir = data_path('pids_filter.txt')
phpsessid_file = data_path('phpsessid.txt')
temp_dir = 'temp'
save_dir = 'saved'
model_path = os.path.join(os.path.abspath("."), 'models', 'nahida_cnn_best.onnx')

# 确保 models 目录存在
model_dir = os.path.join(os.path.abspath("."), 'models')
os.makedirs(model_dir, exist_ok=True)

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
        self.limit_mode = limit_mode  # "图片张数" 或 "PID个数"
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
                    pid_links = link_find(self.php, pid, quality=2)
                    if self.r18_only:
                        if pid_links['R18'] != 1:
                            self.log(f"{pid} 已过滤(非R18)")
                            continue
                    elif pid_links['R18'] != self.r18_rem or pid_links['R18G'] != self.r18g_rem:
                        self.log(f"{pid} 已过滤(r18/r18g类型)")
                        continue
                    # PID内页数超过限制则跳过
                    if self.page_limit_enabled and pid_links['pageCount'] > self.page_limit:
                        self.log(f"{pid} 共 {pid_links['pageCount']} 页，超过限制({self.page_limit}页)，跳过")
                        continue
                    self.log(f"正在下载 PID {pid} ({_index}/{len(pid_list)})，共 {pid_links['pageCount']} 页")
                    for pn in range(1, pid_links['pageCount'] + 1):
                        if self.stop_event.is_set():
                            break
                        if self.limit_mode == "图片张数" and self._check_limit_reached(download_count):
                            break
                        self.check_pause()  # 每张图下载前也检查
                        if self.stop_event.is_set():
                            break
                        page_url = pid_links['links'][pn]['original']
                        page_name = page_url.split('/')[-1]
                        self.log(page_name)
                        if not link_to_image(sub_dir, page_name, page_url, self.php):
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
            pid_links = link_find(self.php, self.pid, quality=4)
            idx = int(self.image_index) if self.image_index is not None else 0
            page_url = pid_links['links'][idx + 1]['original']
            page_name = page_url.split('/')[-1]
            save_path = os.path.join(self.save_subdir, page_name)
            # 检查文件是否已存在
            if os.path.exists(save_path):
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


# ==================== PyQt应用类 ====================
class PixivFilterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pixiv 图片筛选器")
        self._set_app_icon()
        self.setGeometry(100, 100, 1200, 750)

        self.current_index = 0
        self.current_index2 = 0
        
        # 初始化线程变量
        self.search_worker = None
        self.search_thread = None
        self.search_worker2 = None
        self.search_thread2 = None
        self.save_worker = None
        self.save_thread = None
        self.save_worker2 = None
        self.save_thread2 = None
        self._save_pid = None
        self._save_pid2 = None
        # 暂停状态
        self._search_paused = False
        self._search_paused2 = False

        # 每个Tab独立的图片列表
        self.image_list_tab1 = []
        self.image_list_tab2 = []

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

        self.tab_btn3 = QPushButton("  ⚙  设置")
        self.tab_btn3.setFixedHeight(45)
        self.tab_btn3.setStyleSheet("""
            QPushButton { text-align: left; padding: 8px 15px; border: none;
                          color: white; font-size: 13px; background: #2c2c2c; }
            QPushButton:hover { background: #4a4a4a; }
        """)
        self.tab_btn3.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        sidebar_layout.addWidget(self.tab_btn1)
        sidebar_layout.addWidget(self.tab_btn2)
        sidebar_layout.addWidget(self.tab_btn3)
        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)

        # 堆栈面板
        self.stack = QStackedWidget()
        self.tab1 = self.create_filter_tab()
        self.tab2 = self.create_special_filter_tab()
        self.tab3 = self.create_settings_tab()
        self.stack.addWidget(self.tab1)
        self.stack.addWidget(self.tab2)
        self.stack.addWidget(self.tab3)
        self.stack.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack, 1)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 缩放状态（初始化必须在 image_label 创建之后）
        self._zoom1 = 0
        self._zoom2 = 0
        self._pixmap1 = None
        self._pixmap2 = None
        self.image_label.installEventFilter(self)
        self.image_label2.installEventFilter(self)
        # 滚动区域的视口也要安装事件过滤，因为滚轮事件可能被视口拦截
        self.scroll_area.viewport().installEventFilter(self)
        self.scroll_area2.viewport().installEventFilter(self)

        self.update_image_display()

        # 拖拽状态
        self._drag_pos = None

    def eventFilter(self, obj, event):
        # 滚轮缩放
        if event.type() == QEvent.Type.Wheel:
            if obj is self.image_label or obj is self.scroll_area.viewport():
                self._on_wheel(event, 1)
                return True
            elif obj is self.image_label2 or obj is self.scroll_area2.viewport():
                self._on_wheel(event, 2)
                return True

        # 鼠标拖拽移动图片
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            label = self.image_label if obj in (self.image_label, self.scroll_area.viewport()) else \
                    self.image_label2 if obj in (self.image_label2, self.scroll_area2.viewport()) else None
            if label:
                scroll = self.scroll_area if label is self.image_label else self.scroll_area2
                scroll.setCursor(Qt.CursorShape.ClosedHandCursor)
                self._drag_pos = event.globalPosition().toPoint()
                return True

        if event.type() == QEvent.Type.MouseMove and self._drag_pos is not None:
            label = self.image_label if obj in (self.image_label, self.scroll_area.viewport()) else \
                    self.image_label2 if obj in (self.image_label2, self.scroll_area2.viewport()) else None
            if label:
                scroll = self.scroll_area if label is self.image_label else self.scroll_area2
                delta = event.globalPosition().toPoint() - self._drag_pos
                self._drag_pos = event.globalPosition().toPoint()
                h_bar = scroll.horizontalScrollBar()
                v_bar = scroll.verticalScrollBar()
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
                return True

        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if self._drag_pos is not None:
                self._drag_pos = None
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

        search_layout.addWidget(QLabel("搜索页数:"), 0, 2)
        self.pages_spinbox = QSpinBox()
        self.pages_spinbox.setMinimum(1)
        self.pages_spinbox.setMaximum(20)
        self.pages_spinbox.setValue(1)
        search_layout.addWidget(self.pages_spinbox, 0, 3)

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

        pid_layout.addWidget(QLabel("下载限制:"))
        limit_row = QHBoxLayout()
        self.download_limit_spin = QSpinBox()
        self.download_limit_spin.setMinimum(0)
        self.download_limit_spin.setMaximum(9999)
        self.download_limit_spin.setValue(5)
        self.limit_mode_combo = QComboBox()
        self.limit_mode_combo.addItems(["图片张数", "PID个数"])
        limit_row.addWidget(self.download_limit_spin)
        limit_row.addWidget(self.limit_mode_combo)
        pid_layout.addLayout(limit_row)

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

        filter_layout.addWidget(QLabel("搜索页数:"))
        self.pages_spinbox2 = QSpinBox()
        self.pages_spinbox2.setMinimum(1)
        self.pages_spinbox2.setMaximum(20)
        self.pages_spinbox2.setValue(1)
        filter_layout.addWidget(self.pages_spinbox2)

        filter_layout.addWidget(QLabel("下载限制:"))
        limit_row2 = QHBoxLayout()
        self.download_limit_spin2 = QSpinBox()
        self.download_limit_spin2.setMinimum(0)
        self.download_limit_spin2.setMaximum(9999)
        self.download_limit_spin2.setValue(5)
        self.limit_mode_combo2 = QComboBox()
        self.limit_mode_combo2.addItems(["图片张数", "PID个数"])
        limit_row2.addWidget(self.download_limit_spin2)
        limit_row2.addWidget(self.limit_mode_combo2)
        filter_layout.addLayout(limit_row2)

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

        # PID内页数限制设置
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

        page_limit_row.addWidget(QLabel("页则跳过该PID"))
        page_limit_layout.addLayout(page_limit_row)

        page_limit_group.setLayout(page_limit_layout)
        layout.addWidget(page_limit_group)

        # 初始扫描默认 models/ 目录
        self._scan_model_dir(os.path.join(os.path.abspath("."), 'models'))
        self.model_combo.currentIndexChanged.connect(self._on_model_selected)

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
        """检测 PHPSESSID 是否有效"""
        php = self.php_input_global.text().strip()
        if not php:
            self.php_status_label.setText("❌ PHPSESSID 为空")
            self.php_status_label.setStyleSheet("color: red; padding: 4px;")
            return

        self.check_php_btn.setEnabled(False)
        self.check_php_btn.setText("检测中...")
        success, msg = check_pixiv(php)
        self.check_php_btn.setEnabled(True)
        self.check_php_btn.setText("检测")
        self.php_status_label.setText(msg)
        self.php_status_label.setStyleSheet("color: green; padding: 4px;" if success else "color: red; padding: 4px;")

        if success:
            # 写入文件并禁用获取按钮
            with open(phpsessid_file, 'w') as f:
                f.write(php)
            self.get_php_btn.setEnabled(False)
            self.php_status_label.setText("✅ 已保存到 phpsessid.txt")
        else:
            # 检测失败则恢复获取按钮
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
        else:
            self.model_status_label.setText("⚠️ ONNX 模型文件不存在")
            self.model_status_label.setStyleSheet("color: orange; padding: 4px;")
            self.model_identify_checkbox1.setEnabled(False)
            self.model_identify_checkbox2.setEnabled(False)
            self.model_identify_checkbox1.setChecked(False)
            self.model_identify_checkbox2.setChecked(False)

    def _on_page_limit_toggled(self, checked):
        """PID页数限制复选框切换时联动 spinbox"""
        self.page_limit_spin.setEnabled(checked)

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

    def _set_app_icon(self):
        """设置窗口图标（使用 pixiv.ico）"""
        ico_path = resource_path("pixiv.ico")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))

    def update_image_display(self, index=None, label=None):
        if label is None:
            label = self.image_label

        il = self.image_list_tab1 if label is self.image_label else self.image_list_tab2

        if index is None:
            image_path = default_image
            if label is self.image_label:
                self.filename_label.clear()
            else:
                self.filename_label2.clear()
        else:
            image_path = get_image(il, index)
            if image_path is None:
                label.setText("没有更多图片")
                return

        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # 保存原图引用
            if label is self.image_label:
                self._pixmap1 = pixmap
            else:
                self._pixmap2 = pixmap
            # 缩放显示
            zoom = self._zoom1 if label is self.image_label else self._zoom2
            self._apply_zoom(label, zoom)
            fname = os.path.basename(image_path)
            pid = filename_split(fname)
            idx = filename_extract_index(fname)
            display_name = f"{pid}_p{idx}" if idx else pid
            if label is self.image_label:
                self.filename_label.setText(display_name)
            else:
                self.filename_label2.setText(display_name)
        else:
            label.setText(f"图片不存在: {image_path}")
            if label is self.image_label:
                self.filename_label.clear()
            else:
                self.filename_label2.clear()

    def _apply_zoom(self, label, zoom):
        """按缩放因子显示图片，保持宽高比不拉伸"""
        pixmap = self._pixmap1 if label is self.image_label else self._pixmap2
        if pixmap is None or pixmap.isNull():
            return
        # 获取滚动区域视口尺寸（图片实际可显示区域）
        scroll = self.scroll_area if label is self.image_label else self.scroll_area2
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
        zoom = self._zoom1 if tab == 1 else self._zoom2
        if zoom == 0:
            zoom = 1.0
        if event.angleDelta().y() > 0:
            zoom *= 1.2
        else:
            zoom *= 1 / 1.2
        zoom = max(0.1, min(zoom, 10.0))
        if tab == 1:
            self._zoom1 = zoom
        else:
            self._zoom2 = zoom
        label = self.image_label if tab == 1 else self.image_label2
        self._apply_zoom(label, zoom)

    def resizeEvent(self, event):
        """窗口缩放时重绘图片"""
        super().resizeEvent(event)
        if hasattr(self, 'image_label') and self._pixmap1:
            self._apply_zoom(self.image_label, self._zoom1)
        if hasattr(self, 'image_label2') and self._pixmap2:
            self._apply_zoom(self.image_label2, self._zoom2)

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
        self.image_label.clear()
        self.image_label.setText("搜索中...")
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

        # 使用QThread + moveToThread方式处理耗时操作
        self.search_worker = SearchWorker(
            content, php, r18_rem, r18g_rem, int(self.pages_spinbox.value()),
            download_limit=int(self.download_limit_spin.value()),
            limit_mode=self.limit_mode_combo.currentText(),
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
        QMessageBox.critical(self, "错误", f"搜索失败: {msg}")

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
        self.image_label2.clear()
        self.image_label2.setText("搜索中...")
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

        # 使用QThread + moveToThread方式处理耗时操作
        self.search_worker2 = SearchWorker(
            content, php, r18_rem, r18g_rem, int(self.pages_spinbox2.value()),
            download_limit=int(self.download_limit_spin2.value()),
            limit_mode=self.limit_mode_combo2.currentText(),
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
        QMessageBox.critical(self, "错误", f"搜索失败: {msg}")

    # ==================== Tab1 保存 ====================
    def on_save_clicked(self):
        if not (0 <= self.current_index < len(self.image_list_tab1)):
            QMessageBox.warning(self, "警告", "没有有效的图片可保存")
            return

        search_con = self.keywords_input.text().strip()
        if not search_con:
            QMessageBox.warning(self, "警告", "请先输入搜索关键词")
            return

        img_path = self.image_list_tab1[self.current_index]
        image_filename = os.path.basename(img_path)
        image_index = filename_extract_index(image_filename)
        self._save_pid = filename_split(image_filename)
        php = self.php_input_global.text()

        self.save_btn.setEnabled(False)
        self.save_btn.setText("保存中...")

        # 使用QThread + moveToThread方式处理保存操作
        self.save_worker = SaveWorker(os.path.join(save_dir, search_con), php, image_index, self._save_pid)
        self.save_thread = QThread()
        self.save_worker.moveToThread(self.save_thread)
        
        self.save_worker.finished.connect(self._on_save_done)
        self.save_worker.error.connect(self._on_save_error)
        self.save_worker.exists.connect(self._on_save_exists)
        self.save_thread.started.connect(self.save_worker.run)
        self.save_worker.finished.connect(self.save_thread.quit)
        self.save_worker.error.connect(self.save_thread.quit)
        self.save_worker.exists.connect(self.save_thread.quit)
        
        self.save_thread.start()

    def _on_save_done(self):
        if self.pid_filter_checkbox.isChecked():
            pid_filter_add(self._save_pid, True)

        self.save_btn.setEnabled(True)
        self.save_btn.setText("✅ 已保存")
        # 2秒后恢复按钮文字
        QTimer.singleShot(2000, lambda: self.save_btn.setText("✅ 保存") if self.save_btn.text() == "✅ 已保存" else None)

    def _on_save_error(self, msg):
        self.save_btn.setEnabled(True)
        self.save_btn.setText("❌ 失败")
        QTimer.singleShot(2000, lambda: self.save_btn.setText("✅ 保存") if self.save_btn.text() == "❌ 失败" else None)

    def _on_save_exists(self, name):
        self.save_btn.setEnabled(True)
        self.save_btn.setText("✅ 保存")
        QMessageBox.information(self, "提示", f"文件已存在: {name}")

    # ==================== Tab2 保存 ====================
    def on_save_clicked2(self):
        if not (0 <= self.current_index2 < len(self.image_list_tab2)):
            QMessageBox.warning(self, "警告", "没有有效的图片可保存")
            return

        img_path = self.image_list_tab2[self.current_index2]
        image_filename = os.path.basename(img_path)
        image_index = filename_extract_index(image_filename)
        self._save_pid2 = filename_split(image_filename)
        php = self.php_input_global.text()

        self.save_btn2.setEnabled(False)
        self.save_btn2.setText("保存中...")

        # 使用QThread + moveToThread方式处理保存操作
        self.save_worker2 = SaveWorker(os.path.join(save_dir, '纳西妲'), php, image_index, self._save_pid2)
        self.save_thread2 = QThread()
        self.save_worker2.moveToThread(self.save_thread2)
        
        self.save_worker2.finished.connect(self._on_save_done2)
        self.save_worker2.error.connect(self._on_save_error2)
        self.save_worker2.exists.connect(self._on_save_exists2)
        self.save_thread2.started.connect(self.save_worker2.run)
        self.save_worker2.finished.connect(self.save_thread2.quit)
        self.save_worker2.error.connect(self.save_thread2.quit)
        self.save_worker2.exists.connect(self.save_thread2.quit)
        
        self.save_thread2.start()

    def _on_save_done2(self):
        if self.pid_filter_checkbox2.isChecked():
            pid_filter_add(self._save_pid2, True)

        self.save_btn2.setEnabled(True)
        self.save_btn2.setText("✅ 已保存")
        QTimer.singleShot(2000, lambda: self.save_btn2.setText("✅ 保存") if self.save_btn2.text() == "✅ 已保存" else None)

    def _on_save_error2(self, msg):
        self.save_btn2.setEnabled(True)
        self.save_btn2.setText("❌ 失败")
        QTimer.singleShot(2000, lambda: self.save_btn2.setText("✅ 保存") if self.save_btn2.text() == "❌ 失败" else None)

    def _on_save_exists2(self, name):
        self.save_btn2.setEnabled(True)
        self.save_btn2.setText("✅ 保存")
        QMessageBox.information(self, "提示", f"文件已存在: {name}")

    # ==================== 导航：上一张 / 下一张 ====================
    def _reset_save_btn(self):
        """切换图片时恢复保存按钮文字"""
        self.save_btn.setText("✅ 保存")

    def _reset_save_btn2(self):
        self.save_btn2.setText("✅ 保存")

    def on_prev_clicked(self):
        if not self.image_list_tab1:
            return
        if self.current_index > 0:
            self.current_index -= 1
            self.update_image_display(self.current_index)
            self._reset_save_btn()

    def on_next_clicked(self):
        if not self.image_list_tab1:
            return
        if self.current_index < len(self.image_list_tab1) - 1:
            self.current_index += 1
            self.update_image_display(self.current_index)
            self._reset_save_btn()

    def on_prev_clicked2(self):
        if not self.image_list_tab2:
            return
        if self.current_index2 > 0:
            self.current_index2 -= 1
            self.update_image_display(self.current_index2, self.image_label2)
            self._reset_save_btn2()

    def on_next_clicked2(self):
        if not self.image_list_tab2:
            return
        if self.current_index2 < len(self.image_list_tab2) - 1:
            self.current_index2 += 1
            self.update_image_display(self.current_index2, self.image_label2)
            self._reset_save_btn2()

    # ==================== 资源清理 ====================
    def closeEvent(self, event):
        """窗口关闭时清理线程"""
        # 先通知所有 worker 停止
        for worker in [self.search_worker, self.search_worker2]:
            if worker:
                worker.stop_event.set()
        
        # 清理所有运行中的线程
        threads_to_quit = [
            (self.search_thread, self.search_worker),
            (self.search_thread2, self.search_worker2),
            (self.save_thread, self.save_worker),
            (self.save_thread2, self.save_worker2),
        ]
        
        for thread, worker in threads_to_quit:
            if thread and thread.isRunning():
                thread.quit()
                thread.wait(1000)  # 等待最多1秒
                if thread.isRunning():
                    thread.terminate()  # 强制终止
                    thread.wait()
        
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PixivFilterApp()
    window.show()
    sys.exit(app.exec())