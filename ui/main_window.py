# -*- coding: utf-8 -*-
"""
ui/main_window.py — PixivFilterApp 主窗口

从原 test_app.py 的「PyQt应用类」拆出。
界面由 main_window.ui 生成（pyside6-uic → ui_main_window.py），
本类只负责：控件事件、Signal/Slot 接线、线程管理、图片缩放/拖动。
下载/保存/PHPSESSID 等耗时逻辑已拆分到 workers/，纯业务逻辑在 logic/。

⚠️ 修改界面请改 main_window.ui 后重新执行：
    pyside6-uic main_window.ui -o ui_main_window.py
"""

import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMessageBox, QFileDialog
)
from PySide6.QtGui import QPixmap, QIcon, QShortcut, QKeySequence
from PySide6.QtCore import Qt, QThread, QTimer, QEvent

from types import SimpleNamespace

from ui_main_window import Ui_MainWindow
from pixiv_image_download import filename_extract_index

from logic import config_logic
from logic.image_logic import get_image, filename_split, pid_filter_add
from workers.search_worker import SearchWorker, AuthorSearchWorker
from workers.save_worker import SaveWorker
from workers.php_worker import GetPHPSESSIDWorker, CheckPHPSESSIDWorker


# ==================== PyQt应用类 ====================
class PixivFilterApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        # 界面完全来自 main_window.ui（pyside6-uic 生成）
        self.setupUi(self)
        self._set_app_icon()
        self.move(100, 100)

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

        # 背景图 / 子控件透明度（可选；默认无背景图、透明度 0 = 不透明）
        self.background_image = ''
        self.ui_transparency = 0

        # 从配置文件加载上次保存的设置
        self._load_ui_config()

        # 缩放状态（初始化必须在 image_label 创建之后）
        self._zoom1 = 0
        self._zoom2 = 0
        self._zoom3 = 0
        self._pixmap1 = None
        self._pixmap2 = None
        self._pixmap3 = None

        # 拖拽状态
        self._drag_pos = None

        # .ui 无法表达的细节：文件名叠加层不拦截鼠标；图片区左/右 = 5:1
        for lbl in (self.filename_label, self.filename_label2, self.filename_label3):
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        for layout in (self.content_layout1, self.content_layout2, self.content_layout3):
            layout.setStretch(0, 5)
            layout.setStretch(1, 1)

        # 事件过滤：图片区滚轮缩放 / 拖拽（视口也会拦截滚轮，所以一并安装）
        for lbl, scroll in (
            (self.image_label, self.scroll_area),
            (self.image_label2, self.scroll_area2),
            (self.image_label3, self.scroll_area3),
        ):
            lbl.installEventFilter(self)
            scroll.viewport().installEventFilter(self)

        # 信号接线 + 设置页初始化
        self._setup_signals()
        self._init_settings_page()

        # 延迟到窗口显示后再加载默认图片，确保视口尺寸正确（自适应）
        QTimer.singleShot(0, self.update_image_display)

        # 全局快捷键：左右方向键映射到上下一张
        self._shortcut_left = QShortcut(QKeySequence(Qt.Key_Left), self)
        self._shortcut_left.activated.connect(self._on_shortcut_prev)
        self._shortcut_right = QShortcut(QKeySequence(Qt.Key_Right), self)
        self._shortcut_right.activated.connect(self._on_shortcut_next)

    # ==================== 信号接线 / 设置页初始化 ====================
    def _setup_signals(self):
        """集中连接控件信号（界面来自 main_window.ui）"""
        # 侧边栏 → 切换页面
        self.tab_btn1.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.tab_btn2.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.tab_btn3.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.tab_btn4.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        self.stack.currentChanged.connect(self._on_tab_changed)

        # Tab1
        self.search_btn.clicked.connect(self.on_search_clicked)
        self.prev_btn.clicked.connect(self.on_prev_clicked)
        self.next_btn.clicked.connect(self.on_next_clicked)
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.dl_mode_combo1.currentIndexChanged.connect(lambda: self._update_dl_spin(1))
        self.r18_checkbox.stateChanged.connect(lambda: self._update_r18_state(1))
        self.r18g_checkbox.stateChanged.connect(lambda: self._update_r18_state(1))
        self.r18_only_checkbox.stateChanged.connect(lambda: self._update_r18_state(1))

        # Tab2
        self.search_btn2.clicked.connect(self.on_search_clicked2)
        self.prev_btn2.clicked.connect(self.on_prev_clicked2)
        self.next_btn2.clicked.connect(self.on_next_clicked2)
        self.save_btn2.clicked.connect(self.on_save_clicked2)
        self.stop_btn2.clicked.connect(self._on_stop_clicked2)
        self.dl_mode_combo2.currentIndexChanged.connect(lambda: self._update_dl_spin(2))
        self.r18_checkbox2.stateChanged.connect(lambda: self._update_r18_state(2))
        self.r18g_checkbox2.stateChanged.connect(lambda: self._update_r18_state(2))
        self.r18_only_checkbox2.stateChanged.connect(lambda: self._update_r18_state(2))

        # Tab3
        self.search_btn3.clicked.connect(self.on_search_clicked3)
        self.prev_btn3.clicked.connect(self.on_prev_clicked3)
        self.next_btn3.clicked.connect(self.on_next_clicked3)
        self.save_btn3.clicked.connect(self.on_save_clicked3)
        self.stop_btn3.clicked.connect(self._on_stop_clicked3)
        self.r18_checkbox3.stateChanged.connect(lambda: self._update_r18_state(3))
        self.r18g_checkbox3.stateChanged.connect(lambda: self._update_r18_state(3))
        self.r18_only_checkbox3.stateChanged.connect(lambda: self._update_r18_state(3))

        # 设置页
        self.php_input_global.textChanged.connect(self._on_php_input_changed)
        self.get_php_btn.clicked.connect(self._on_get_phpsessid)
        self.check_php_btn.clicked.connect(self._on_check_phpsessid)
        self.browse_model_btn.clicked.connect(self._on_browse_model_dir)
        self.model_combo.currentIndexChanged.connect(self._on_model_selected)
        self.page_limit_checkbox.toggled.connect(self._on_page_limit_toggled)
        self.set_bg_image_btn.clicked.connect(self._on_bg_apply)
        self.delete_bg_image_btn.clicked.connect(self._on_bg_delete)
        self.browse_bg_image_btn.clicked.connect(self._on_browse_bg_image)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)

        # 初始 R18 互斥状态
        self._update_r18_state(1)
        self._update_r18_state(2)
        self._update_r18_state(3)

    def _init_settings_page(self):
        """设置页初始化：PHPSESSID 回填、扫描模型目录与默认图片"""
        self.php_input_global.setText(config_logic.phpsessid)
        # 初始扫描默认 models/ 目录
        self._scan_model_dir(os.path.join(os.path.abspath("."), 'models'))
        # 扫描可选背景图（theme/default_image + theme/added_image）
        self._scan_background_images()
        if self.background_image:
            self.bg_status_label.setText(f"当前背景图: {os.path.basename(self.background_image)}")
        else:
            self.bg_status_label.setText("未设置背景图（选择后点「设置」生效）")
        # 透明度滑杆回填（blockSignals 避免初始化时触发保存）
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(self.ui_transparency)
        self.opacity_slider.blockSignals(False)
        self.opacity_value_label.setText(f"{self.ui_transparency}%")
        # 应用背景图 + 子控件透明度
        self._apply_appearance()

    def _update_r18_state(self, tab):
        """R18 / R18G / 仅R18 三者互斥（按 tab 处理）"""
        if tab == 1:
            r18, r18g, only = self.r18_checkbox, self.r18g_checkbox, self.r18_only_checkbox
        elif tab == 2:
            r18, r18g, only = self.r18_checkbox2, self.r18g_checkbox2, self.r18_only_checkbox2
        else:
            r18, r18g, only = self.r18_checkbox3, self.r18g_checkbox3, self.r18_only_checkbox3
        r18_any = r18.isChecked() or r18g.isChecked()
        r18_only = only.isChecked()
        r18.setEnabled(not r18_only)
        r18g.setEnabled(not r18_only)
        only.setEnabled(not r18_any)

    def _update_dl_spin(self, tab):
        """下载方式切换时联动 spin（页数模式最多20，其它最多100，并重置为1）"""
        if tab == 1:
            combo, spin = self.dl_mode_combo1, self.dl_spin1
        else:
            combo, spin = self.dl_mode_combo2, self.dl_spin2
        m = combo.currentText()
        spin.setMaximum(20 if m == "页数模式" else 100)
        spin.setValue(1)

    # ==================== 配置读写 ====================

    # ==================== 配置读写 ====================
    def _load_ui_config(self):
        """从 config/config.json 加载背景图与子控件透明度"""
        cfg = config_logic.load_ui_config()
        bg = cfg.get('background_image') or ''
        if bg and not os.path.exists(bg):
            bg = ''
        self.background_image = bg
        try:
            v = int(cfg.get('ui_transparency', 0))
        except (TypeError, ValueError):
            v = 0
        self.ui_transparency = max(0, min(100, v))

    def _save_ui_config(self):
        """保存背景图与子控件透明度到 config/config.json"""
        config_logic.save_ui_config(self.background_image, self.ui_transparency)

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

    # ==================== Tab3：作者作品 ====================
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
            with open(config_logic.phpsessid_file, 'w') as f:
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
        path = self.model_combo.currentData()
        if path and os.path.exists(path):
            config_logic.model_path = path
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

    # ==================== 背景图 / 子控件透明度 ====================
    def _scan_background_images(self):
        """扫描 theme/default_image 与 theme/added_image，填充背景图下拉"""
        combo = self.bg_image_combo
        combo.blockSignals(True)
        combo.clear()

        exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
        image_entries = []
        seen = set()

        # 同名文件 added_image 覆盖 default_image
        dirs = [
            ('default', os.path.join(os.path.abspath("."), 'theme', 'default_image')),
            ('added', os.path.join(os.path.abspath("."), 'theme', 'added_image')),
        ]
        for tag, d in dirs:
            if os.path.isdir(d):
                for f in sorted(os.listdir(d)):
                    if f.lower().endswith(exts) and os.path.isfile(os.path.join(d, f)):
                        path = os.path.normpath(os.path.abspath(os.path.join(d, f)))
                        key = f.lower()
                        if key not in seen:
                            image_entries.append((f, path, tag))
                            seen.add(key)
                        else:
                            for i, (name, p, t) in enumerate(image_entries):
                                if name.lower() == key:
                                    image_entries[i] = (f, path, tag)
                                    break

        default_entries = sorted([e for e in image_entries if e[2] == 'default'], key=lambda x: x[0].lower())
        added_entries = sorted([e for e in image_entries if e[2] == 'added'], key=lambda x: x[0].lower())

        if image_entries:
            for fname, path, tag in default_entries + added_entries:
                if tag == 'default':
                    display = f"预设{os.path.splitext(fname)[0]}"
                else:
                    display = f"{fname} ({os.path.relpath(path, os.path.abspath('.'))})"
                combo.addItem(display, path)
        else:
            combo.addItem("（未找到图片文件）", "")

        # 在最前面插入"无"选项
        combo.insertItem(0, "无", "")

        # 选中当前已保存的背景图
        idx = self._find_img_combo_index(combo, self.background_image)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    @staticmethod
    def _norm_path(p):
        """规范化路径：统一分隔符并忽略大小写（便于跨写法匹配）"""
        return os.path.normcase(os.path.normpath(p))

    def _find_img_combo_index(self, combo, path):
        """在下拉列表中查找与 path 对应的项索引；找不到返回 -1"""
        if not path:
            return -1
        norm = self._norm_path(path)
        base = os.path.basename(norm)
        count = combo.count()
        # 1) 全路径精确匹配（兼容正/反斜杠混用）
        for i in range(count):
            data = combo.itemData(i)
            if data and self._norm_path(data) == norm:
                return i
        # 2) 仅按文件名匹配
        for i in range(count):
            data = combo.itemData(i)
            if data and os.path.basename(self._norm_path(data)) == base:
                return i
        return -1

    def _on_bg_apply(self):
        """「设置」：让下拉中选定的背景图生效（index 0 = 无）"""
        index = self.bg_image_combo.currentIndex()
        if index < 0:
            return
        if index == 0:
            path = ""
        else:
            path = self.bg_image_combo.currentData()
            if not path or not os.path.exists(path):
                return
        self.background_image = path
        self._save_ui_config()
        self._apply_appearance()
        if path:
            self.bg_status_label.setText(f"✅ 已设置背景图: {self.bg_image_combo.currentText()}")
        else:
            self.bg_status_label.setText("已关闭背景图")

    def _on_bg_delete(self):
        """「删除」：移除下拉中选定项，并删除 theme/added_image 中对应文件"""
        index = self.bg_image_combo.currentIndex()
        if index <= 0:
            QMessageBox.information(self, "提示", "请先在列表中选择要删除的背景图。")
            return
        path = self.bg_image_combo.currentData()
        if not path:
            return

        added_dir = os.path.normpath(os.path.join(os.path.abspath("."), 'theme', 'added_image'))
        if os.path.normcase(os.path.dirname(os.path.normpath(path))) != os.path.normcase(added_dir):
            QMessageBox.information(
                self, "提示",
                "该图是预设背景图（theme/default_image），不能删除。\n"
                "只有通过「添加」导入到 theme/added_image 的图片才能删除。"
            )
            return

        name = os.path.basename(path)
        ans = QMessageBox.question(
            self, "确认删除", f"确定从 theme/added_image 删除该背景图文件吗？\n{name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            QMessageBox.warning(self, "删除失败", f"无法删除文件：{e}")
            return

        # 若正在使用这张图，则清空背景
        if path and self._norm_path(self.background_image or '') == self._norm_path(path):
            self.background_image = ''
            self._save_ui_config()
            self._apply_appearance()

        self._scan_background_images()
        self.bg_status_label.setText(f"🗑 已删除: {name}")

    def _on_browse_bg_image(self):
        """浏览并选择一张背景图，复制到 theme/added_image 并设为背景"""
        added_dir = os.path.join(os.path.abspath("."), 'theme', 'added_image')
        os.makedirs(added_dir, exist_ok=True)
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图", added_dir,
            "图片文件 (*.jpg *.jpeg *.png *.gif *.webp *.bmp);;所有文件 (*)"
        )
        if not file_path:
            return
        import shutil
        fname = os.path.basename(file_path)
        dest_path = os.path.normpath(os.path.join(added_dir, fname))
        same = (os.path.normcase(os.path.abspath(file_path))
                == os.path.normcase(os.path.abspath(dest_path)))
        if not same:
            try:
                shutil.copy2(file_path, dest_path)
            except shutil.SameFileError:
                pass  # 源文件本来就在 added_image 里

        self._scan_background_images()
        idx = self._find_img_combo_index(self.bg_image_combo, dest_path)
        if idx >= 0:
            self.bg_image_combo.setCurrentIndex(idx)
        # 原逻辑：添加后立即使新图生效
        self._on_bg_apply()
        self.bg_status_label.setText(f"✅ 已添加背景图: {fname}")

    def _on_opacity_changed(self, value):
        """子控件透明度滑杆（0 = 不透明(默认)，100 = 全透明；只改背景色，不动文字）"""
        self.ui_transparency = int(value)
        self.opacity_value_label.setText(f"{value}%")
        self._save_ui_config()
        self._apply_appearance()

    def _ensure_bg_label(self):
        """背景图用一个铺底 QLabel 绘制（保持在所有子控件下方）"""
        if getattr(self, '_bg_label', None) is None:
            lbl = QLabel(self.centralwidget)
            lbl.setObjectName('bg_label')
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            lbl.setAlignment(Qt.AlignCenter)
            self._bg_label = lbl
        return self._bg_label

    def _update_bg_pixmap(self):
        """背景图等比缩放并居中（KeepAspectRatio，绝不拉伸）：
        横向图则左右顶满、竖向图则上下顶满，装不下的方向居中留空。"""
        lbl = self._ensure_bg_label()
        path = self.background_image
        if not path or not os.path.exists(path):
            self._bg_pixmap = None
            self._bg_pixmap_path = None
            lbl.clear()
            lbl.hide()
            return
        if getattr(self, '_bg_pixmap_path', None) != path:
            self._bg_pixmap = QPixmap(path)
            self._bg_pixmap_path = path
        if self._bg_pixmap is None or self._bg_pixmap.isNull():
            lbl.hide()
            return
        size = self.centralwidget.size()
        if size.width() <= 1 or size.height() <= 1:
            return
        scaled = self._bg_pixmap.scaled(size, Qt.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
        lbl.setPixmap(scaled)
        lbl.resize(size)
        lbl.move(0, 0)
        lbl.lower()   # 保持在侧边栏 / 堆栈面板下方
        lbl.show()

    def _apply_appearance(self):
        """背景图（等比不拉伸）+ 子控件背景（白色 + 透明度）。

        - 白色背景只画在 QGroupBox 的边框（黑线）**以内**（显式指定 border）；
        - 图片显示区（QScrollArea）的背景同样受透明度控制；
        - 输入类控件不参与，保持不透明、文字清晰；
        - 页面空处固定透明，用来露出背景图。
        """
        self._update_bg_pixmap()

        # 透明度 0 → alpha=1（白色不透明）；透明度 100 → alpha=0（背景全透明）
        alpha = 1.0 - (self.ui_transparency / 100.0)
        qss = (
            "QStackedWidget#stack { background: transparent; }\n"
            "QWidget#tab1, QWidget#tab2, QWidget#tab3, QWidget#tab4 { background: transparent; }\n"
            "QGroupBox {\n"
            "    border: 1px solid #808080;\n"
            "    border-radius: 8px;\n"
            f"    background-color: rgba(255, 255, 255, {alpha:.3f});\n"
            "}\n"
        )
        self.stack.setStyleSheet(qss)

        # 图片显示区：背景也由透明度控制（白色画在边框以内），视口透明
        for sa in (self.scroll_area, self.scroll_area2, self.scroll_area3):
            sa.setStyleSheet(
                f"QScrollArea {{ background-color: rgba(255, 255, 255, {alpha:.3f}); "
                "border: 1px solid #808080; }"
            )
            sa.viewport().setStyleSheet("background: transparent;")

    # ==================== Tab3 搜索 ====================
    # ==================== 多 Tab 通用逻辑（tab: 1/2/3） ====================
    def _tab_ctx(self, tab):
        """收集某个 Tab 的控件与状态引用，供通用搜索/导航逻辑复用"""
        if tab == 1:
            return SimpleNamespace(
                search_btn=self.search_btn, save_btn=self.save_btn,
                prev_btn=self.prev_btn, next_btn=self.next_btn,
                stop_btn=self.stop_btn, info=self.info_box, label=self.image_label,
                image_list=self.image_list_tab1, model_cb=self.model_identify_checkbox1,
                index_attr='current_index', worker_attr='search_worker',
                thread_attr='search_thread', paused_attr='_search_paused',
            )
        if tab == 2:
            return SimpleNamespace(
                search_btn=self.search_btn2, save_btn=self.save_btn2,
                prev_btn=self.prev_btn2, next_btn=self.next_btn2,
                stop_btn=self.stop_btn2, info=self.info_box2, label=self.image_label2,
                image_list=self.image_list_tab2, model_cb=self.model_identify_checkbox2,
                index_attr='current_index2', worker_attr='search_worker2',
                thread_attr='search_thread2', paused_attr='_search_paused2',
            )
        return SimpleNamespace(
            search_btn=self.search_btn3, save_btn=self.save_btn3,
            prev_btn=self.prev_btn3, next_btn=self.next_btn3,
            stop_btn=self.stop_btn3, info=self.info_box3, label=self.image_label3,
            image_list=self.image_list_tab3, model_cb=None,
            index_attr='current_index3', worker_attr='search_worker3',
            thread_attr='search_thread3', paused_attr='_search_paused3',
        )

    def _toggle_search_pause(self, tab):
        """若该 Tab 正在搜索：处理“停止后重启 / 继续 / 暂停”；返回 True 表示已处理"""
        ctx = self._tab_ctx(tab)
        thread = getattr(self, ctx.thread_attr)
        if not (thread and thread.isRunning()):
            return False
        worker = getattr(self, ctx.worker_attr)
        paused = getattr(self, ctx.paused_attr)
        if worker and worker.stop_event.is_set():
            # 已发过停止信号：等待退出后清空，允许重新搜索
            thread.quit()
            thread.wait(500)
            if thread.isRunning():
                thread.terminate()
                thread.wait()
            setattr(self, ctx.worker_attr, None)
            setattr(self, ctx.thread_attr, None)
            ctx.search_btn.setText("🔍 搜索")
            setattr(self, ctx.paused_attr, False)
            ctx.stop_btn.setVisible(False)
        elif paused:
            # 继续下载
            worker.pause_event.clear()
            setattr(self, ctx.paused_attr, False)
            ctx.search_btn.setText("⏸ 暂停")
            ctx.info.append("▶ 继续下载")
        else:
            # 暂停下载
            worker.pause_event.set()
            setattr(self, ctx.paused_attr, True)
            ctx.search_btn.setText("▶ 继续")
            ctx.info.append("⏸ 已暂停")
        return True

    def _stop_search(self, tab):
        """停止某 Tab 的搜索"""
        ctx = self._tab_ctx(tab)
        worker = getattr(self, ctx.worker_attr)
        if worker:
            worker.stop_event.set()
        ctx.search_btn.setText("🔍 搜索")
        setattr(self, ctx.paused_attr, False)
        ctx.stop_btn.setVisible(False)
        ctx.info.append("⏹ 已停止搜索")

    def _finish_search(self, tab):
        """搜索正常结束（无结果时提示）"""
        ctx = self._tab_ctx(tab)
        ctx.search_btn.setEnabled(True)
        ctx.search_btn.setText("🔍 搜索")
        setattr(self, ctx.paused_attr, False)
        if ctx.model_cb is not None:
            ctx.model_cb.setEnabled(True)
        ctx.stop_btn.setVisible(False)
        if not ctx.image_list:
            QMessageBox.information(self, "提示", "没有找到符合条件的图片")
            self.update_image_display(label=ctx.label)

    def _search_failed(self, tab, msg):
        """搜索异常结束：展示真实原因（无结果时弹窗）"""
        ctx = self._tab_ctx(tab)
        ctx.search_btn.setEnabled(True)
        ctx.search_btn.setText("🔍 搜索")
        setattr(self, ctx.paused_attr, False)
        ctx.save_btn.setEnabled(False)
        ctx.prev_btn.setEnabled(False)
        ctx.next_btn.setEnabled(False)
        if ctx.model_cb is not None:
            ctx.model_cb.setEnabled(True)
        ctx.stop_btn.setVisible(False)
        # 尚未获得任何结果时，弹窗提示真实失败原因（如 PHPSESSID 过期），而不是误报“没有找到图片”
        if not ctx.image_list:
            QMessageBox.critical(self, "搜索失败", f"{msg}")
        ctx.info.append(f"❌ 搜索失败: {msg}")

    def _add_image_ready(self, tab, path):
        """每下载完一张图立即更新展示"""
        ctx = self._tab_ctx(tab)
        ctx.image_list.append(path)
        if len(ctx.image_list) == 1:
            setattr(self, ctx.index_attr, 0)
            self.update_image_display(0, ctx.label)
            # 第一张图到了就启用操作按钮
            ctx.save_btn.setEnabled(True)
            ctx.prev_btn.setEnabled(True)
            ctx.next_btn.setEnabled(True)

    def _navigate(self, tab, delta, first_msg="已经是第一张啦~", last_msg="已经是最后一张啦~"):
        """上一张 / 下一张导航"""
        ctx = self._tab_ctx(tab)
        if not ctx.image_list:
            return
        idx = getattr(self, ctx.index_attr)
        if delta < 0:
            if idx > 0:
                idx -= 1
                setattr(self, ctx.index_attr, idx)
                self.update_image_display(idx, ctx.label)
                self._update_save_btn_state(ctx.image_list, idx, ctx.save_btn)
            else:
                self.show_toast(first_msg, "warning", 1500)
        else:
            if idx < len(ctx.image_list) - 1:
                idx += 1
                setattr(self, ctx.index_attr, idx)
                self.update_image_display(idx, ctx.label)
                self._update_save_btn_state(ctx.image_list, idx, ctx.save_btn)
            else:
                self.show_toast(last_msg, "warning", 1500)

    def on_search_clicked3(self):
        """按作者ID搜索"""
        if self._toggle_search_pause(3):
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
            model_path=config_logic.model_path,
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
        # 作者页结束行为与 Tab1/2 略有不同（记录作者名 + 成功 toast），故单独实现
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
        self._add_image_ready(3, path)

    def _on_search_error3(self, msg):
        self._search_failed(3, msg)

    def _on_stop_clicked3(self):
        self._stop_search(3)

    # ==================== Tab3 导航 ====================
    def on_prev_clicked3(self):
        self._navigate(3, -1)

    def on_next_clicked3(self):
        self._navigate(3, 1)

    def _on_tab_changed(self, index):
        """切换标签时更新侧边栏按钮样式（白底半透明 + 深色文字）"""
        active = """
            QPushButton { text-align: left; padding: 8px 15px; border: none;
                          color: #222; font-size: 13px; background: rgba(0, 0, 0, 40); }
            QPushButton:hover { background: rgba(0, 0, 0, 60); }
        """
        inactive = """
            QPushButton { text-align: left; padding: 8px 15px; border: none;
                          color: #444; font-size: 13px; background: transparent; }
            QPushButton:hover { background: rgba(0, 0, 0, 30); }
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
        ico_path = config_logic.resource_path("pixiv.ico")
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
            # 无默认图：清空为空白，让背景图透出
            filename_lbl.clear()
            label.clear()
            label.setPixmap(QPixmap())
            if label is self.image_label:
                self._pixmap1 = None
            elif label is self.image_label2:
                self._pixmap2 = None
            else:
                self._pixmap3 = None
            return
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
        """窗口缩放时重绘图片与背景图"""
        super().resizeEvent(event)
        if hasattr(self, 'centralwidget'):
            self._update_bg_pixmap()
        if hasattr(self, 'image_label') and self._pixmap1:
            self._apply_zoom(self.image_label, self._zoom1)
        if hasattr(self, 'image_label2') and self._pixmap2:
            self._apply_zoom(self.image_label2, self._zoom2)
        if hasattr(self, 'image_label3') and self._pixmap3:
            self._apply_zoom(self.image_label3, self._zoom3)

    # ==================== Tab1 搜索 ====================
    def on_search_clicked(self):
        # 已有 worker 在运行 → 暂停/继续切换
        if self._toggle_search_pause(1):
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
            model_path=config_logic.model_path,
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
        self._stop_search(1)

    def _on_search_done(self, result):
        self._finish_search(1)

    def _on_image_ready(self, path):
        """每下载完一张图立即更新展示"""
        self._add_image_ready(1, path)

    def _on_search_error(self, msg):
        self._search_failed(1, msg)

    # ==================== Tab2 搜索 ====================
    def on_search_clicked2(self):
        # 已有 worker 在运行 → 暂停/继续切换
        if self._toggle_search_pause(2):
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
            model_path=config_logic.model_path,
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
        self._stop_search(2)

    def _on_search_done2(self, result):
        self._finish_search(2)

    def _on_image_ready2(self, path):
        """每下载完一张图立即更新展示 (Tab2)"""
        self._add_image_ready(2, path)

    def _on_search_error2(self, msg):
        self._search_failed(2, msg)

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
            os.path.join(config_logic.save_dir, search_con),
            self.save_btn, '_save_pid',
            self.pid_filter_checkbox
        )

    def on_save_clicked2(self):
        """Tab2 保存"""
        self._do_save(
            os.path.join(config_logic.save_dir, '纳西妲'),
            self.save_btn2, '_save_pid2',
            self.pid_filter_checkbox2
        )

    def on_save_clicked3(self):
        """Tab3 保存"""
        author_subdir = getattr(self, '_author_name', None) or self.author_id_input.text().strip()
        self._do_save(
            os.path.join(config_logic.save_dir, author_subdir),
            self.save_btn3, '_save_pid3',
            self.pid_filter_checkbox3
        )

    # ==================== 导航：上一张 / 下一张 ====================
    def on_prev_clicked(self):
        self._navigate(1, -1)

    def on_next_clicked(self):
        self._navigate(1, 1)

    def on_prev_clicked2(self):
        self._navigate(2, -1, "已是第一张", "已是最后一张")

    def on_next_clicked2(self):
        self._navigate(2, 1, "已是第一张", "已是最后一张")

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
