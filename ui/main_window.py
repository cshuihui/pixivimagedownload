# -*- coding: utf-8 -*-
"""
ui/main_window.py — PixivFilterApp 主窗口

界面由 main_window.ui 生成（pyside6-uic → ui_main_window.py），
本类只负责：控件事件、Signal/Slot 接线、线程管理、图片缩放/拖动。
下载/保存/PHPSESSID 等耗时逻辑已拆分到 workers/，纯业务逻辑在 logic/。

⚠️ 修改界面请改 main_window.ui 后重新执行：
    pyside6-uic main_window.ui -o ui_main_window.py
"""

import os
import shutil

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMessageBox, QFileDialog,
    QGraphicsDropShadowEffect, QWidget
)
from PySide6.QtGui import (
    QPixmap, QIcon, QShortcut, QKeySequence, QColor, QPainter, QPainterPath,
    QPen, QRegion, QDesktopServices
)
from PySide6.QtCore import (
    Qt, QThread, QTimer, QEvent, QPoint, QPointF, QRect, QRectF, QSize, QUrl
)

from types import SimpleNamespace

from ui_main_window import Ui_MainWindow
from pixiv_image_download import filename_extract_index

from logic import config_logic
from logic.image_logic import get_image, filename_split, pid_filter_add
from workers.search_worker import SearchWorker, AuthorSearchWorker, PidSearchWorker
from workers.save_worker import SaveWorker
from workers.php_worker import GetPHPSESSIDWorker, CheckPHPSESSIDWorker


# ==================== PyQt应用类 ====================
class PixivFilterApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        # 界面完全来自 main_window.ui（pyside6-uic 生成）
        self.setupUi(self)
        self._set_app_icon()
        # 无边框窗口：页眉改由 main_window.ui 里的自定义 titlebar 承担
        # （左侧 app_icon + app_title，右侧 min_btn / max_btn / close_btn）
        # 圆角的前提：窗口自身透明，不透明背景交给 card 自己画
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint   # 保留系统菜单 → Alt+F4 可关闭
        )
        self.setMouseTracking(True)

        # 统一样式表（ui/app.qss）
        self._load_app_qss()
        # 卡片外阴影：main_window.ui 的 main_layout 已留出 16px 透明边距
        self._card_shadow = QGraphicsDropShadowEffect(self)
        self._card_shadow.setBlurRadius(12)
        self._card_shadow.setOffset(0, 2)
        self._card_shadow.setColor(QColor(0, 0, 0, 80))
        self.card.setGraphicsEffect(self._card_shadow)
        # 卡片尺寸变化时重算背景图（窗口 resizeEvent 触发时 card 还是旧尺寸，
        # 必须等布局算完，因此监听 card 自己的 Resize 事件）
        self.card.installEventFilter(self)
        # 自定义最大化状态（无边框窗口自行管理，铺满屏幕工作区）
        self._maximized_custom = False
        self._normal_geometry = None
        # 页眉三颗按钮的图标：QPainter 自绘（比字形干净，且各 DPI 下都清晰）
        self._setup_window_buttons()
        self.move(100, 100)

        self.current_index = 0
        self.current_index2 = 0
        self.current_index3 = 0
        self.current_index4 = 0

        # 初始化线程变量
        self.search_worker = None
        self.search_thread = None
        self.search_worker2 = None
        self.search_thread2 = None
        self.search_worker3 = None
        self.search_thread3 = None
        self.search_worker4 = None
        self.search_thread4 = None
        self.save_worker = None
        self.save_thread = None
        self.save_worker2 = None
        self.save_thread2 = None
        self.save_worker3 = None
        self.save_thread3 = None
        self._save_pid = None
        self._save_pid2 = None
        self._save_pid3 = None
        self._save_pid4 = None
        # 暂停状态
        self._search_paused = False
        self._search_paused2 = False
        self._search_paused3 = False
        self._search_paused4 = False

        # 保存线程池（允许并发保存）
        self._save_threads3 = []

        # 每个Tab独立的图片列表
        self.image_list_tab1 = []
        self.image_list_tab2 = []
        self.image_list_tab3 = []
        self.image_list_tab4 = []

        # 背景图 / 子控件透明度（默认预设 1 背景图、透明度 20）
        self.background_image = config_logic.default_image
        self.ui_transparency = 20

        # 从配置文件加载上次保存的设置
        self._load_ui_config()

        # 缩放状态（初始化必须在 image_label 创建之后）
        self._zoom1 = 0
        self._zoom2 = 0
        self._zoom3 = 0
        self._zoom4 = 0
        self._pixmap1 = None
        self._pixmap2 = None
        self._pixmap3 = None
        self._pixmap4 = None

        # 拖拽状态
        self._drag_pos = None
        # 无边框窗口的拖动状态
        self._win_drag_pos = None
        # 无边框窗口的缩放状态（自己实现，不走系统缩放循环）
        self._resize_edges = None
        self._resize_origin = None
        self._resize_start_geo = None

        # .ui 无法表达的细节：文件名叠加层不拦截鼠标；图片区左/右 = 5:1
        for lbl in (self.filename_label, self.filename_label2, self.filename_label3,
                    self.filename_label4):
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        # 侧边栏 tab 文字加粗
        for btn in (self.tab_btn1, self.tab_btn2, self.tab_btn3,
                    self.tab_btn4, self.tab_btn5):
            f = btn.font()
            f.setBold(True)
            btn.setFont(f)
        for layout in (self.content_layout1, self.content_layout2, self.content_layout3,
                       self.content_layout4):
            layout.setStretch(0, 5)
            layout.setStretch(1, 1)

        # 事件过滤：图片区滚轮缩放 / 拖拽（视口也会拦截滚轮，所以一并安装）
        for lbl, scroll in (
            (self.image_label, self.scroll_area),
            (self.image_label2, self.scroll_area2),
            (self.image_label3, self.scroll_area3),
            (self.image_label4, self.scroll_area4),
        ):
            lbl.installEventFilter(self)
            scroll.viewport().installEventFilter(self)

        # 信号接线 + 设置页初始化
        self._setup_signals()
        self._init_settings_page()
        # 打开鼠标跟踪，否则鼠标靠近窗口边缘时收不到移动事件、不会变缩放光标
        self._enable_hover_tracking()

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
        self.tab_btn5.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        self.stack.currentChanged.connect(self._on_tab_changed)
        # 侧边栏最下方：在资源管理器中打开下载目录
        self.open_download_btn.clicked.connect(self._on_open_download_dir)

        # 自定义页眉（标题栏）：最小化 / 最大化-还原 / 关闭
        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self._toggle_max_restore)
        self.close_btn.clicked.connect(self.close)

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

        # Tab4 (PID)
        self.search_btn4.clicked.connect(self.on_search_clicked4)
        self.prev_btn4.clicked.connect(self.on_prev_clicked4)
        self.next_btn4.clicked.connect(self.on_next_clicked4)
        self.save_btn4.clicked.connect(self.on_save_clicked4)
        self.stop_btn4.clicked.connect(self._on_stop_clicked4)
        # PID 页没有过滤选项，因此不接 R18 互斥逻辑

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
        self.clear_cache_btn.clicked.connect(self._on_clear_cache)

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
        # 卡片圆角 / 阴影 / 边距（依赖 _maximized_custom，须在窗口状态就绪后再调用）
        self._apply_card_state()
        # 缓存大小
        self._update_cache_size()

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
        """从 config/config.json 加载背景图、子控件透明度、PHPSESSID

        - 没有 background_image 键（首次运行）→ 用 theme/default_image 的预设 1；
        - 显式存空字符串 → 用户主动选了「无」，保持为空；
        - 存了路径 → 还原成绝对路径（项目换目录后按文件名自动找回），
          若还原结果与存的不一致，顺手把 config 规范化写回。
        """
        cfg = config_logic.load_ui_config()
        has_key = 'background_image' in cfg
        stored = cfg.get('background_image') or ''
        if not has_key:
            bg = config_logic.default_image       # 首次运行
        elif not stored:
            bg = ''                               # 用户显式「无」
        else:
            bg = config_logic.resolve_stored_path(stored)
        self.background_image = bg

        try:
            v = int(cfg.get('ui_transparency', 20))
        except (TypeError, ValueError):
            v = 20
        self.ui_transparency = max(0, min(100, v))
        self.phpsessid = cfg.get('phpsessid') or ''

        # 旧配置里存的是绝对路径（换目录后会失效）→ 规范化写回，避免下次再丢
        if has_key and bg and \
                config_logic.to_stored_path(bg) != stored.replace('\\', '/'):
            self._save_ui_config()

    def _save_ui_config(self):
        """保存背景图、子控件透明度、PHPSESSID 到 config/config.json

        背景图存相对路径（项目内的文件），保证换目录后仍能加载。
        """
        config_logic.save_ui_config(
            config_logic.to_stored_path(self.background_image),
            self.ui_transparency, getattr(self, 'phpsessid', '') or ''
        )

    # ==================== 样式表 / 卡片圆角与阴影 ====================
    _CARD_RADIUS = 10      # 需与 ui/app.qss 中 #card 的 border-radius 一致
    _SHADOW_MARGIN = 16    # 需与 main_window.ui 中 main_layout 的边距一致

    def _load_app_qss(self):
        """加载 ui/app.qss 统一样式表

        开发态从工作目录取；打包后由 resource_path 定位到解包目录。
        """
        qss_path = config_logic.resource_path(os.path.join('ui', 'app.qss'))
        if not os.path.exists(qss_path):
            qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.qss')
        try:
            with open(qss_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        except OSError as e:
            print(f"加载样式表失败: {e}")

    def _apply_card_state(self):
        """按「最大化 / 常规」状态应用圆角、阴影与四周边距

        最大化时必须关掉圆角与阴影：铺满屏幕时圆角会露出四角豁口，
        阴影则会在屏幕边缘形成一圈光晕。
        """
        maximized = self._maximized_custom
        flag = "true" if maximized else "false"
        # 属性名用 winMaximized：QWidget 已有内置只读属性 maximized，
        # 用那个名字 setProperty 会静默失败，QSS 选择器就永远匹配不上
        for w in (self.card, self.titlebar, self.sidebar):
            w.setProperty("winMaximized", flag)
            w.style().unpolish(w)
            w.style().polish(w)
        if getattr(self, '_card_shadow', None) is not None:
            self._card_shadow.setEnabled(not maximized)
        m = 0 if maximized else self._SHADOW_MARGIN
        self.main_layout.setContentsMargins(m, m, m, m)
        self._update_bg_pixmap()   # 背景图需按当前圆角重新裁切

    # ==================== 无边框窗口：拖动移动 / 边缘缩放 ====================
    _RESIZE_MARGIN = 6

    def _edge_at(self, local_pos):
        """判断鼠标位于卡片哪条边/角（无边框窗口的缩放热区）

        热区贴着「可见」的卡片边缘，而不是窗口外沿 —— 窗口四周另有 16px
        透明阴影边距，若按窗口矩形判定，用户得把鼠标移出可见范围才能缩放。
        """
        m = self._RESIZE_MARGIN
        tl = self.card.mapTo(self, QPoint(0, 0))
        br = self.card.mapTo(self, QPoint(self.card.width(), self.card.height()))
        # 卡片尺寸异常小（布局还没算完）时不判定热区，
        # 否则任意位置都会落进 ±m 范围内，整条页眉都会被当成边缘
        if br.x() - tl.x() <= 2 * m or br.y() - tl.y() <= 2 * m:
            return None
        x, y = local_pos.x(), local_pos.y()
        left = x <= tl.x() + m
        right = x >= br.x() - m
        top = y <= tl.y() + m
        bottom = y >= br.y() - m
        edges = None
        for edge, on in ((Qt.Edge.LeftEdge, left), (Qt.Edge.RightEdge, right),
                         (Qt.Edge.TopEdge, top), (Qt.Edge.BottomEdge, bottom)):
            if on:
                edges = edge if edges is None else (edges | edge)
        return edges

    def _update_resize_cursor(self, local_pos):
        edges = self._edge_at(local_pos)
        if edges is None:
            self.unsetCursor()
            return
        if edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edges in (Qt.Edge.TopEdge, Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edges == (Qt.Edge.LeftEdge | Qt.Edge.TopEdge) or \
                edges == (Qt.Edge.RightEdge | Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)

    def _in_titlebar(self, global_pos):
        """该全局坐标是否落在页眉空白处（三颗按钮不算）"""
        if getattr(self, 'titlebar', None) is None:
            return False
        pos = self.titlebar.mapFromGlobal(global_pos)
        if not self.titlebar.rect().contains(pos):
            return False
        for btn in (self.min_btn, self.max_btn, self.close_btn):
            if btn.geometry().contains(pos):
                return False
        return True

    def _enable_hover_tracking(self):
        """给窗口所有子控件打开鼠标跟踪

        子控件默认不跟踪鼠标：没有按键的鼠标移动事件根本不会送到窗口，
        「鼠标靠近窗口边缘 → 变成缩放光标」的提示就永远不会出现。
        """
        for w in [self] + self.findChildren(QWidget):
            w.setMouseTracking(True)

    def _begin_resize(self, edges, global_pos):
        """开始缩放：记下起点与起始几何（自己实现，不用系统缩放循环）"""
        self._resize_edges = edges
        self._resize_origin = global_pos
        self._resize_start_geo = self.geometry()

    def _do_resize(self, global_pos):
        """按当前鼠标位置更新窗口几何（左/上边靠移动 x/y 实现缩放）"""
        if self._resize_edges is None or self._resize_start_geo is None:
            return
        geo = QRect(self._resize_start_geo)
        dx = global_pos.x() - self._resize_origin.x()
        dy = global_pos.y() - self._resize_origin.y()
        min_size = self.minimumSizeHint()
        min_w = max(self.minimumWidth(), min_size.width())
        min_h = max(self.minimumHeight(), min_size.height())
        if self._resize_edges & Qt.Edge.LeftEdge:
            geo.setLeft(min(geo.left() + dx, geo.right() - min_w + 1))
        elif self._resize_edges & Qt.Edge.RightEdge:
            geo.setRight(max(geo.right() + dx, geo.left() + min_w - 1))
        if self._resize_edges & Qt.Edge.TopEdge:
            geo.setTop(min(geo.top() + dy, geo.bottom() - min_h + 1))
        elif self._resize_edges & Qt.Edge.BottomEdge:
            geo.setBottom(max(geo.bottom() + dy, geo.top() + min_h - 1))
        self.setGeometry(geo)

    def _reset_gestures(self):
        """清空「拖动窗口 / 缩放窗口」状态

        每次按下、松开、窗口失焦都调一次：即使上一次的松开事件因平台原因
        （鼠标跑到窗口外、被别的程序抢走等）没送到，也不会留下残留状态
        —— 否则下次按页眉拖窗口会被残留的缩放状态抢走，变成改窗口大小。
        """
        self._win_drag_pos = None
        self._resize_edges = None
        self._resize_origin = None
        self._resize_start_geo = None

    def mousePressEvent(self, event):
        """左键：窗口四条边/四角 → 缩放；页眉 → 拖动；其它地方不做任何改变"""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        gp = event.globalPosition().toPoint()
        self._reset_gestures()      # 按下时先把上一次的手势状态清干净

        # ① 四条边 / 四角 → 缩放（最大化时不处理）
        if not self._maximized_custom:
            edges = self._edge_at(self.mapFromGlobal(gp))
            if edges is not None:
                self._begin_resize(edges, gp)
                event.accept()
                return

        # ② 只有页眉能移动窗口
        if not self._in_titlebar(gp):
            super().mousePressEvent(event)
            return

        # ③ 最大化时页眉单击不做任何事：要还原请双击页眉或点 ❐ 按钮
        if self._maximized_custom:
            event.accept()
            return

        self._win_drag_pos = gp - self.frameGeometry().topLeft()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        """双击页眉 → 最大化 / 还原（与系统标题栏行为一致）

        不用 titlebar 的事件过滤器：窗口拖动会 accept 页眉上的按下并持有
        隐式鼠标抓取，Qt 会把随后的双击发给窗口本身，过滤器收不到。
        """
        if event.button() == Qt.MouseButton.LeftButton and \
                self._in_titlebar(event.globalPosition().toPoint()):
            self._reset_gestures()       # 双击不当作拖动 / 缩放
            self._toggle_max_restore()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        gp = event.globalPosition().toPoint()
        held = bool(event.buttons() & Qt.MouseButton.LeftButton)

        # 没有按住左键：手势结束（顺便兼容“松开事件丢了”的情况）
        if not held:
            if self._resize_edges is not None or self._win_drag_pos is not None:
                self._reset_gestures()
            self._update_resize_cursor(self.mapFromGlobal(gp))
            super().mouseMoveEvent(event)
            return

        # 缩放中
        if self._resize_edges is not None and self._resize_start_geo is not None:
            self._do_resize(gp)
            event.accept()
            return
        # 拖动中（仅页眉会进入这个状态）
        if self._win_drag_pos is not None:
            self.move(gp - self._win_drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 松开时不再做任何几何操作（避免窗口莫名位移）
            self._reset_gestures()
        super().mouseReleaseEvent(event)

    def changeEvent(self, event):
        """窗口失活（Alt+Tab / 点到别的程序）时结束手势，避免状态残留"""
        if event.type() == QEvent.Type.ActivationChange and \
                not self.isActiveWindow() and hasattr(self, '_resize_edges'):
            self._reset_gestures()
        super().changeEvent(event)

    def eventFilter(self, obj, event):
        # 卡片尺寸变化（首帧 / 缩放 / 最大化）→ 重算背景图。
        # 窗口 resizeEvent 触发时 card 的几何还没被布局更新，必须等这之后。
        if obj is getattr(self, 'card', None) and event.type() == QEvent.Type.Resize:
            self._update_bg_pixmap()
            return False

        # 图片展示框尺寸变化 → 重算圆角遮罩（遮罩必须跟着尺寸走）
        if event.type() == QEvent.Type.Resize and hasattr(self, 'scroll_area'):
            for sa in self._image_scroll_areas():
                if obj is sa.viewport():
                    self._apply_rounded_mask(sa)
                    self._apply_rounded_mask(sa.viewport())
                    break

        # 页眉：双击空白处 → 最大化 / 还原（与系统标题栏行为一致）
        if obj is getattr(self, 'titlebar', None) and \
                event.type() == QEvent.Type.MouseButtonDblClick:
            self._toggle_max_restore()
            return True

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

        # 鼠标拖拽平移图片
        # 注意：这里必须用「左键是否按住」来判定，不能只看 _drag_pos 是否非空 ——
        # 现在窗口开了鼠标跟踪（为了让边缘出缩放光标），没有按键的移动事件也会
        # 送到过滤器；若残留了 _drag_pos，图片就会一直跟着鼠标跑。
        if event.type() == QEvent.Type.MouseButtonPress and \
                event.button() == Qt.MouseButton.LeftButton:
            pair = self._image_area_of(obj)
            if pair is not None:
                scroll, _label = pair
                scroll.setCursor(Qt.CursorShape.ClosedHandCursor)
                self._drag_pos = event.globalPosition().toPoint()
                return True

        if event.type() == QEvent.Type.MouseMove:
            held = bool(event.buttons() & Qt.MouseButton.LeftButton)
            if self._drag_pos is not None and not held:
                self._drag_pos = None       # 没按住就结束平移（兼容松开事件丢失）
            elif self._drag_pos is not None:
                pair = self._image_area_of(obj)
                if pair is not None:
                    scroll, _label = pair
                    delta = event.globalPosition().toPoint() - self._drag_pos
                    self._drag_pos = event.globalPosition().toPoint()
                    h_bar = scroll.horizontalScrollBar()
                    v_bar = scroll.verticalScrollBar()
                    h_bar.setValue(h_bar.value() - delta.x())
                    v_bar.setValue(v_bar.value() - delta.y())
                    return True

        if event.type() == QEvent.Type.MouseButtonRelease and \
                event.button() == Qt.MouseButton.LeftButton:
            pair = self._image_area_of(obj)
            if pair is not None:
                scroll, _label = pair
                scroll.setCursor(Qt.CursorShape.ArrowCursor)
            self._drag_pos = None          # 关键：松开一定要清掉，否则图片会跟着鼠标
            return True

        return super().eventFilter(obj, event)

    def _image_area_of(self, obj):
        """obj 属于哪个图片显示区 → (scroll, label)；都不属于返回 None"""
        for scroll, label in ((self.scroll_area, self.image_label),
                              (self.scroll_area2, self.image_label2),
                              (self.scroll_area3, self.image_label3)):
            if obj is label or obj is scroll.viewport():
                return scroll, label
        return None

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
            self.phpsessid = php
            self._save_ui_config()
            self.get_php_btn.setEnabled(False)
            self.php_status_label.setText("✅ 已保存到 config.json")
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

    def _cache_size_bytes(self):
        """temp 目录占用的字节数"""
        total = 0
        if os.path.isdir(config_logic.temp_dir):
            for root, _dirs, files in os.walk(config_logic.temp_dir):
                for name in files:
                    try:
                        total += os.path.getsize(os.path.join(root, name))
                    except OSError:
                        pass
        return total

    @staticmethod
    def _human_size(num):
        """字节数转为易读字符串"""
        size = float(num)
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024 or unit == 'GB':
                return f"{int(size)} {unit}" if unit == 'B' else f"{size:.1f} {unit}"
            size /= 1024.0

    def _update_cache_size(self):
        """刷新缓存大小显示"""
        self.cache_size_label.setText(self._human_size(self._cache_size_bytes()))

    def _on_clear_cache(self):
        """清理 temp 缓存目录"""
        try:
            if os.path.isdir(config_logic.temp_dir):
                shutil.rmtree(config_logic.temp_dir)
            os.makedirs(config_logic.temp_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, "清理失败", f"无法清理缓存：{e}")
            return
        self._update_cache_size()
        self.show_toast("🧹 缓存已清理", "success", 1500)

    # ==================== 打开下载目录 ====================
    def _on_open_download_dir(self):
        """在系统文件管理器中打开下载（保存）目录 saved/"""
        path = os.path.abspath(config_logic.save_dir)
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法创建下载目录：\n{path}\n\n{e}")
            return
        # QDesktopServices 跨平台，打包后同样可用（os.startfile 仅 Windows）
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            QMessageBox.warning(self, "打开失败", f"无法打开目录：\n{path}")

    def _ensure_bg_label(self):
        """背景图用一个铺底 QLabel 绘制（保持在所有子控件下方）

        挂在 card 上（而不是 centralwidget），这样它被限制在卡片范围内，
        并且能在代码里按卡片圆角做裁切 —— 子控件不会被父级 border-radius 裁剪。
        """
        if getattr(self, '_bg_label', None) is None:
            lbl = QLabel(self.card)
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
            self._bg_render_key = None
            lbl.clear()
            lbl.hide()
            return
        if getattr(self, '_bg_pixmap_path', None) != path:
            self._bg_pixmap = QPixmap(path)
            self._bg_pixmap_path = path
            self._bg_render_key = None      # 换了图片文件，必须重绘
        if self._bg_pixmap is None or self._bg_pixmap.isNull():
            self._bg_render_key = None
            lbl.hide()
            return
        size = self.card.size()
        if size.width() <= 1 or size.height() <= 1:
            return

        # 尺寸 / 圆角都没变就跳过重绘：本函数会被窗口拖动缩放高频触发，
        # 每次都做一遍 SmoothTransformation 缩放开销很大（保持幂等）
        radius = 0 if self._maximized_custom else self._CARD_RADIUS
        key = (size.width(), size.height(), radius)
        if getattr(self, '_bg_render_key', None) == key:
            return

        scaled = self._bg_pixmap.scaled(size, Qt.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)

        # 按卡片圆角裁切（子控件不受父级 border-radius 约束，必须自己裁）
        canvas = QPixmap(size)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if radius > 0:
            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, size.width(), size.height()),
                                radius, radius)
            painter.setClipPath(path)
        painter.drawPixmap((size.width() - scaled.width()) // 2,
                           (size.height() - scaled.height()) // 2, scaled)
        painter.end()

        lbl.setPixmap(canvas)
        lbl.resize(size)
        lbl.move(0, 0)
        lbl.lower()   # 保持在侧边栏 / 堆栈面板下方
        lbl.show()
        self._bg_render_key = key   # 记录本次渲染尺寸，重复调用直接跳过

    # ==================== 图片展示框（圆角 / 角标文案） ====================
    _IMG_BOX_RADIUS = 8

    def _image_scroll_areas(self):
        """四个 Tab 的图片展示框（QScrollArea）"""
        return (self.scroll_area, self.scroll_area2,
                self.scroll_area3, self.scroll_area4)

    def _apply_rounded_mask(self, widget):
        """给控件套圆角遮罩

        QSS 的 border-radius 只影响边框绘制，并不会裁剪子控件（图片会从
        圆角外露出来），所以这里显式用 QRegion 做遮罩；尺寸变化时必须重算。
        """
        size = widget.size()
        if size.width() <= 1 or size.height() <= 1:
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, size.width(), size.height()),
                            self._IMG_BOX_RADIUS, self._IMG_BOX_RADIUS)
        widget.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _filename_label_of(self, image_label):
        """图片 label → 同 Tab 的文件名角标 label"""
        if image_label is self.image_label:
            return self.filename_label
        if image_label is self.image_label2:
            return self.filename_label2
        if image_label is self.image_label3:
            return self.filename_label3
        if image_label is self.image_label4:
            return self.filename_label4
        return None

    @staticmethod
    def _format_filename(path, total, index):
        """角标文案：文件名 + 「, 序号/总数」（序号从 1 开始）

        例：136626738_p0, 3/12
        """
        fname = os.path.basename(path)
        pid = filename_split(fname)
        idx = filename_extract_index(fname)
        name = f"{pid}_p{idx}" if idx else pid
        if index is not None and total and 0 <= index < total:
            return f"{name}, {index + 1}/{total}"
        return name

    def _refresh_filename_count(self, tab):
        """预览图数量变化时只刷新角标文字（不重渲染图片，避免重复缩放开销）"""
        ctx = self._tab_ctx(tab)
        idx = getattr(self, ctx.index_attr)
        if not ctx.image_list or not (0 <= idx < len(ctx.image_list)):
            return
        lbl = self._filename_label_of(ctx.label)
        if lbl is not None:
            lbl.setText(self._format_filename(ctx.image_list[idx],
                                              len(ctx.image_list), idx))

    def _apply_appearance(self):
        """背景图（等比不拉伸）+ 子控件背景（白色 + 透明度）。

        - 白色背景只画在 QGroupBox 的边框（灰线）**以内**（显式指定 border）；
        - 图片显示区（QScrollArea）的背景同样受透明度控制；
        - 输入类控件不参与，保持不透明、文字清晰；
        - 页面空处固定透明，用来露出背景图。
        """
        self._update_bg_pixmap()

        # 透明度 0 → alpha=1（白色不透明）；透明度 100 → alpha=0（背景全透明）
        alpha = 1.0 - (self.ui_transparency / 100.0)
        qss = (
            "QStackedWidget#stack { background: transparent; }\n"
            "QWidget#tab1, QWidget#tab2, QWidget#tab3, QWidget#tab4, "
            "QWidget#tab5 { background: transparent; }\n"
            "QGroupBox {\n"
            "    border: 1px solid #808080;\n"
            "    border-radius: 8px;\n"
            f"    background-color: rgba(255, 255, 255, {alpha:.3f});\n"
            "}\n"
        )
        self.stack.setStyleSheet(qss)

        # 图片显示区：背景也由透明度控制（白色画在边框以内），视口透明。
        # 边框原写在 main_window.ui 各 scroll_area 的 inline 样式里，现收敛到此处
        # 统一管理 —— 只有这里能同时写入随滑块变化的 alpha。
        for sa in self._image_scroll_areas():
            sa.setStyleSheet(
                f"QScrollArea {{ background-color: rgba(255, 255, 255, {alpha:.3f}); "
                f"border: 1px solid gray; border-radius: {self._IMG_BOX_RADIUS}px; }}"
            )
            sa.viewport().setStyleSheet("background: transparent;")
            self._apply_rounded_mask(sa)
            self._apply_rounded_mask(sa.viewport())

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
        if tab == 4:
            return SimpleNamespace(
                search_btn=self.search_btn4, save_btn=self.save_btn4,
                prev_btn=self.prev_btn4, next_btn=self.next_btn4,
                stop_btn=self.stop_btn4, info=self.info_box4, label=self.image_label4,
                image_list=self.image_list_tab4, model_cb=None,
                index_attr='current_index4', worker_attr='search_worker4',
                thread_attr='search_thread4', paused_attr='_search_paused4',
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
        else:
            # 总数变了：只刷角标的「序号/总数」，不重渲染图片
            self._refresh_filename_count(tab)

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

    # ==================== Tab4 搜索（按作品 PID） ====================
    def on_search_clicked4(self):
        """按作品 PID 搜索：下载该作品的全部预览图"""
        if self._toggle_search_pause(4):
            return

        pid = self.pid_input.text().strip()
        if not pid:
            QMessageBox.warning(self, "警告", "请输入作品ID(PID)")
            return

        php = self.php_input_global.text()
        self.php_session = php

        self.image_list_tab4.clear()
        self.image_label4.setPixmap(QPixmap())
        self.image_label4.setText("搜索中...")
        self.image_label4.repaint()
        QApplication.processEvents()
        self.info_box4.clear()

        self.search_btn4.setEnabled(True)
        self.search_btn4.setText("搜索中...")
        self.save_btn4.setEnabled(False)
        self.prev_btn4.setEnabled(False)
        self.next_btn4.setEnabled(False)
        self.stop_btn4.setVisible(True)
        self._search_paused4 = False

        # PID 页按用户要求不做任何过滤：输入哪个 PID 就下哪个
        self.search_worker4 = PidSearchWorker(pid, php)
        self.search_thread4 = QThread()
        self.search_worker4.moveToThread(self.search_thread4)

        self.search_worker4.finished.connect(self._on_search_done4)
        self.search_worker4.image_ready.connect(self._on_image_ready4)
        self.search_worker4.log_msg.connect(self.info_box4.append)
        self.search_worker4.error.connect(self._on_search_error4)
        self.search_thread4.started.connect(self.search_worker4.run)
        self.search_worker4.finished.connect(self.search_thread4.quit)
        self.search_worker4.error.connect(self.search_thread4.quit)

        self.search_thread4.start()

    def _on_search_done4(self, result):
        self._finish_search(4)
        if self.image_list_tab4:
            self.show_toast(f"✅ 下载完毕！共 {len(self.image_list_tab4)} 张图片",
                            "success", 3000)

    def _on_image_ready4(self, path):
        self._add_image_ready(4, path)

    def _on_search_error4(self, msg):
        self._search_failed(4, msg)

    def _on_stop_clicked4(self):
        self._stop_search(4)

    # ==================== Tab3 导航 ====================
    def on_prev_clicked3(self):
        self._navigate(3, -1)

    def on_next_clicked3(self):
        self._navigate(3, 1)

    # ==================== Tab4 导航 ====================
    def on_prev_clicked4(self):
        self._navigate(4, -1, "已是第一张", "已是最后一张")

    def on_next_clicked4(self):
        self._navigate(4, 1, "已是第一张", "已是最后一张")

    def _on_tab_changed(self, index):
        """切换标签时更新侧边栏按钮选中态

        样式本身写在 ui/app.qss（#tab_btnN[active="true"]），这里只翻转动态属性，
        避免为「选中 / 未选中」各维护一份手写样式。
        """
        for i, btn in enumerate((self.tab_btn1, self.tab_btn2, self.tab_btn3,
                                 self.tab_btn4, self.tab_btn5)):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # 进入设置页时刷新缓存大小（设置页现在是第 5 个，索引 4）
        if index == 4:
            self._update_cache_size()

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
        elif index == 3 and self._pixmap4 is None:
            QTimer.singleShot(0, lambda: self.update_image_display(label=self.image_label4))
        elif index == 3 and self._pixmap4 is not None:
            QTimer.singleShot(0, lambda: self._apply_zoom(self.image_label4, self._zoom4))

    # ==================== 自定义页眉：最小化 / 最大化 / 关闭 ====================
    # 图标逻辑尺寸（按钮 44x30，字形 16x16 视觉最舒服）
    _WIN_ICON_SIZE = 16
    # 三颗按钮尺寸 + 页眉内边距：都在代码里设定，.ui 文件暂不修改
    # （页眉高 38，上下各留 4 → 4 + 30 + 4 = 38 正好装下）
    _WIN_BTN_W = 44
    _WIN_BTN_H = 30
    _TITLEBAR_MARGINS = (10, 4, 6, 4)   # 左, 上, 右, 下

    def _make_win_glyph(self, kind, color, size=None, dpr=1.0):
        """用 QPainter 画一个页眉按钮字形，返回 QPixmap。

        kind: min（横线）/ max（方框）/ restore（双框）/ close（叉）
        """
        s = float(size or self._WIN_ICON_SIZE)
        pm = QPixmap(int(round(s * dpr)), int(round(s * dpr)))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.GlobalColor.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor(color))
        pen.setWidthF(1.25)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        p.setPen(pen)

        m = s * 0.27                 # 四周留白
        w = s - 2 * m
        if kind == 'min':
            y = round(s / 2 - 0.5) + 0.5      # 半像素对齐，横线更锐利
            p.drawLine(QPointF(m, y), QPointF(s - m, y))
        elif kind == 'max':
            p.drawRect(QRectF(m, m, w, w))
        elif kind == 'restore':
            d = w * 0.42                      # 前后两个方框的错位量
            p.drawRect(QRectF(m, m + d, w - d, w - d))
            p.drawPolyline([QPointF(m + d, m), QPointF(s - m, m),
                            QPointF(s - m, s - m - d)])
        elif kind == 'close':
            p.drawLine(QPointF(m, m), QPointF(s - m, s - m))
            p.drawLine(QPointF(s - m, m), QPointF(m, s - m))
        p.end()
        return pm

    def _build_win_icons(self):
        """构建三颗按钮的 QIcon：正常灰 → 悬停加深（关闭键悬停变白）"""
        icons = {}
        for kind, hover in (('min', '#111111'), ('max', '#111111'),
                            ('restore', '#111111'), ('close', '#ffffff')):
            icon = QIcon()
            for dpr in (1.0, 1.5, 2.0, 3.0):     # 多分辨率，适配缩放屏
                icon.addPixmap(self._make_win_glyph(kind, '#555555', dpr=dpr))
                icon.addPixmap(self._make_win_glyph(kind, hover, dpr=dpr),
                               QIcon.Mode.Active)
            icons[kind] = icon
        return icons

    def _setup_window_buttons(self):
        """给页眉三颗按钮贴自绘图标（文字字形全部弃用）

        按钮尺寸与页眉内边距都在这里用代码定：main_window.ui 暂不修改，
        等界面定稿后再统一重写 .ui。
        """
        self._win_icons = self._build_win_icons()
        icon_size = QSize(self._WIN_ICON_SIZE, self._WIN_ICON_SIZE)
        for btn in (self.min_btn, self.max_btn, self.close_btn):
            btn.setText('')
            btn.setIconSize(icon_size)
            btn.setFixedSize(self._WIN_BTN_W, self._WIN_BTN_H)
        # 内边距跟着调，保证按钮四周都有留白（悬停底色不贴边）
        self.titlebar_layout.setContentsMargins(*self._TITLEBAR_MARGINS)
        self.min_btn.setIcon(self._win_icons['min'])
        self.close_btn.setIcon(self._win_icons['close'])
        self._sync_max_btn()

    def _toggle_max_restore(self):
        """最大化 / 还原（无边框窗口，铺满屏幕可用工作区）"""
        if self._maximized_custom:
            if self._normal_geometry is not None:
                self.setGeometry(self._normal_geometry)
            self._maximized_custom = False
        else:
            self._normal_geometry = self.geometry()
            screen = self.screen() or QApplication.primaryScreen()
            if screen is not None:
                self.setGeometry(screen.availableGeometry())
            self._maximized_custom = True
        self._apply_card_state()
        self._sync_max_btn()

    def _sync_max_btn(self):
        """切换最大化按钮的图标与提示（□ / ❐ 为自绘图标）"""
        if getattr(self, 'max_btn', None) is None:
            return
        icons = getattr(self, '_win_icons', None)
        if icons is None:
            return
        if self._maximized_custom:
            self.max_btn.setIcon(icons['restore'])
            self.max_btn.setToolTip('还原')
        else:
            self.max_btn.setIcon(icons['max'])
            self.max_btn.setToolTip('最大化')

    def _set_app_icon(self):
        """设置窗口图标，并把同一图标贴到自定义页眉最左侧。

        图标文件放在项目根目录，按顺序找 pixiv.ico → pixiv.png；
        找不到就把页眉左侧的图标位隐藏。
        """
        for name in ('pixiv.ico', 'pixiv.png'):
            ico_path = config_logic.resource_path(name)
            if not os.path.exists(ico_path):
                continue
            self.setWindowIcon(QIcon(ico_path))
            pm = QPixmap(ico_path)
            if pm.isNull() or getattr(self, 'app_icon', None) is None:
                continue
            self.app_icon.setPixmap(pm.scaled(
                22, 22, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            return
        if getattr(self, 'app_icon', None) is not None:
            self.app_icon.hide()

    def update_image_display(self, index=None, label=None):
        if label is None:
            label = self.image_label

        if label is self.image_label:
            il = self.image_list_tab1
            filename_lbl = self.filename_label
        elif label is self.image_label2:
            il = self.image_list_tab2
            filename_lbl = self.filename_label2
        elif label is self.image_label3:
            il = self.image_list_tab3
            filename_lbl = self.filename_label3
        else:
            il = self.image_list_tab4
            filename_lbl = self.filename_label4

        if index is None:
            # 无默认图：清空为空白，让背景图透出
            filename_lbl.clear()
            label.clear()
            label.setPixmap(QPixmap())
            if label is self.image_label:
                self._pixmap1 = None
            elif label is self.image_label2:
                self._pixmap2 = None
            elif label is self.image_label3:
                self._pixmap3 = None
            else:
                self._pixmap4 = None
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
            elif label is self.image_label3:
                self._pixmap3 = pixmap
                zoom = self._zoom3
            else:
                self._pixmap4 = pixmap
                zoom = self._zoom4
            self._apply_zoom(label, zoom)
            filename_lbl.setText(self._format_filename(image_path, len(il), index))
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
        elif label is self.image_label3:
            pixmap = self._pixmap3
            scroll = self.scroll_area3
        else:
            pixmap = self._pixmap4
            scroll = self.scroll_area4
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
        zoom = {1: self._zoom1, 2: self._zoom2,
                3: self._zoom3, 4: self._zoom4}.get(tab, self._zoom1)
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
        elif tab == 3:
            self._zoom3 = zoom
            label = self.image_label3
        else:
            self._zoom4 = zoom
            label = self.image_label4
        self._apply_zoom(label, zoom)

    def resizeEvent(self, event):
        """窗口缩放时重绘图片与背景图"""
        super().resizeEvent(event)
        if hasattr(self, 'card'):
            self._update_bg_pixmap()
        if hasattr(self, 'image_label') and self._pixmap1:
            self._apply_zoom(self.image_label, self._zoom1)
        if hasattr(self, 'image_label2') and self._pixmap2:
            self._apply_zoom(self.image_label2, self._zoom2)
        if hasattr(self, 'image_label3') and self._pixmap3:
            self._apply_zoom(self.image_label3, self._zoom3)
        if hasattr(self, 'image_label4') and self._pixmap4:
            self._apply_zoom(self.image_label4, self._zoom4)

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

    # ==================== 统一保存方法（Tab1/Tab2/Tab3/Tab4 共用） ====================
    def _do_save(self, save_subdir, btn, pid_attr, filter_checkbox):
        """统一的保存逻辑

        Args:
            save_subdir: 保存子目录 (saved/{关键词}/)
            btn: 对应的保存按钮 (save_btn / save_btn2 / save_btn3)
            pid_attr: 存储 pid 的属性名，如 '_save_pid'
            filter_checkbox: pid 屏蔽复选框；传 None 表示该 Tab 没有此选项（如 PID 页）
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
        elif btn is self.save_btn3:
            img_list = self.image_list_tab3
            idx = self.current_index3
            image_label = self.image_label3
        else:
            img_list = self.image_list_tab4
            idx = self.current_index4
            image_label = self.image_label4

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
        if worker._filter_checkbox is not None and worker._filter_checkbox.isChecked():
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
        elif worker._btn is self.save_btn3:
            self._update_save_btn_state(self.image_list_tab3, self.current_index3, self.save_btn3)
        else:
            self._update_save_btn_state(self.image_list_tab4, self.current_index4, self.save_btn4)

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

    def on_save_clicked4(self):
        """Tab4(PID) 保存：以 PID 作为保存目录（无 pid 屏蔽勾选框，传 None）"""
        pid = self.pid_input.text().strip() or 'PID'
        self._do_save(
            os.path.join(config_logic.save_dir, pid),
            self.save_btn4, '_save_pid4',
            None
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
        elif tab == 3:
            self.on_prev_clicked4()

    def _on_shortcut_next(self):
        """全局快捷键：→ 下一张"""
        tab = self.stack.currentIndex()
        if tab == 0:
            self.on_next_clicked()
        elif tab == 1:
            self.on_next_clicked2()
        elif tab == 2:
            self.on_next_clicked3()
        elif tab == 3:
            self.on_next_clicked4()

    # ==================== 资源清理 ====================
    def closeEvent(self, event):
        """窗口关闭时清理线程"""
        # 先通知所有 worker 停止
        for worker in [self.search_worker, self.search_worker2,
                       self.search_worker3, self.search_worker4]:
            if worker:
                worker.stop_event.set()

        # 清理所有运行中的线程
        threads_to_quit = [
            (self.search_thread, self.search_worker),
            (self.search_thread2, self.search_worker2),
            (self.search_thread3, self.search_worker3),
            (self.search_thread4, self.search_worker4),
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
