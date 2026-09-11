# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QSlider, QSpacerItem, QSpinBox, QStackedWidget,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1200, 750)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.main_layout = QHBoxLayout(self.centralwidget)
        self.main_layout.setSpacing(0)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = QWidget(self.centralwidget)
        self.sidebar.setObjectName(u"sidebar")
        self.sidebar.setMinimumSize(QSize(130, 0))
        self.sidebar.setMaximumSize(QSize(130, 16777215))
        self.sidebar.setStyleSheet(u"background-color: rgba(255, 255, 255, 180);")
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setSpacing(0)
        self.sidebar_layout.setObjectName(u"sidebar_layout")
        self.sidebar_layout.setContentsMargins(0, 10, 0, 10)
        self.tab_btn1 = QPushButton(self.sidebar)
        self.tab_btn1.setObjectName(u"tab_btn1")
        self.tab_btn1.setMinimumSize(QSize(0, 45))
        self.tab_btn1.setMaximumSize(QSize(16777215, 45))
        self.tab_btn1.setStyleSheet(u"QPushButton { text-align: left; padding: 8px 15px; border: none;\n"
"              color: #222; font-size: 13px; background: rgba(0, 0, 0, 40); }\n"
"QPushButton:hover { background: rgba(0, 0, 0, 60); }")

        self.sidebar_layout.addWidget(self.tab_btn1)

        self.tab_btn2 = QPushButton(self.sidebar)
        self.tab_btn2.setObjectName(u"tab_btn2")
        self.tab_btn2.setMinimumSize(QSize(0, 45))
        self.tab_btn2.setMaximumSize(QSize(16777215, 45))
        self.tab_btn2.setStyleSheet(u"QPushButton { text-align: left; padding: 8px 15px; border: none;\n"
"              color: #444; font-size: 13px; background: transparent; }\n"
"QPushButton:hover { background: rgba(0, 0, 0, 30); }")

        self.sidebar_layout.addWidget(self.tab_btn2)

        self.tab_btn3 = QPushButton(self.sidebar)
        self.tab_btn3.setObjectName(u"tab_btn3")
        self.tab_btn3.setMinimumSize(QSize(0, 45))
        self.tab_btn3.setMaximumSize(QSize(16777215, 45))
        self.tab_btn3.setStyleSheet(u"QPushButton { text-align: left; padding: 8px 15px; border: none;\n"
"              color: #444; font-size: 13px; background: transparent; }\n"
"QPushButton:hover { background: rgba(0, 0, 0, 30); }")

        self.sidebar_layout.addWidget(self.tab_btn3)

        self.tab_btn4 = QPushButton(self.sidebar)
        self.tab_btn4.setObjectName(u"tab_btn4")
        self.tab_btn4.setMinimumSize(QSize(0, 45))
        self.tab_btn4.setMaximumSize(QSize(16777215, 45))
        self.tab_btn4.setStyleSheet(u"QPushButton { text-align: left; padding: 8px 15px; border: none;\n"
"              color: #444; font-size: 13px; background: transparent; }\n"
"QPushButton:hover { background: rgba(0, 0, 0, 30); }")

        self.sidebar_layout.addWidget(self.tab_btn4)

        self.sidebar_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.sidebar_layout.addItem(self.sidebar_spacer)


        self.main_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget(self.centralwidget)
        self.stack.setObjectName(u"stack")
        self.tab1 = QWidget()
        self.tab1.setObjectName(u"tab1")
        self.tab1_layout = QVBoxLayout(self.tab1)
        self.tab1_layout.setObjectName(u"tab1_layout")
        self.search_group1 = QGroupBox(self.tab1)
        self.search_group1.setObjectName(u"search_group1")
        self.search_layout1 = QGridLayout(self.search_group1)
        self.search_layout1.setObjectName(u"search_layout1")
        self.label_keywords = QLabel(self.search_group1)
        self.label_keywords.setObjectName(u"label_keywords")

        self.search_layout1.addWidget(self.label_keywords, 0, 0, 1, 1)

        self.keywords_input = QLineEdit(self.search_group1)
        self.keywords_input.setObjectName(u"keywords_input")

        self.search_layout1.addWidget(self.keywords_input, 0, 1, 1, 1)

        self.label_filter = QLabel(self.search_group1)
        self.label_filter.setObjectName(u"label_filter")

        self.search_layout1.addWidget(self.label_filter, 1, 0, 1, 1)

        self.filter_row1 = QHBoxLayout()
        self.filter_row1.setObjectName(u"filter_row1")
        self.r18_checkbox = QCheckBox(self.search_group1)
        self.r18_checkbox.setObjectName(u"r18_checkbox")
        self.r18_checkbox.setChecked(True)

        self.filter_row1.addWidget(self.r18_checkbox)

        self.r18g_checkbox = QCheckBox(self.search_group1)
        self.r18g_checkbox.setObjectName(u"r18g_checkbox")
        self.r18g_checkbox.setChecked(True)

        self.filter_row1.addWidget(self.r18g_checkbox)

        self.r18_only_checkbox = QCheckBox(self.search_group1)
        self.r18_only_checkbox.setObjectName(u"r18_only_checkbox")

        self.filter_row1.addWidget(self.r18_only_checkbox)


        self.search_layout1.addLayout(self.filter_row1, 1, 1, 1, 1, Qt.AlignLeft)


        self.tab1_layout.addWidget(self.search_group1)

        self.content_layout1 = QHBoxLayout()
        self.content_layout1.setObjectName(u"content_layout1")
        self.left_layout1 = QVBoxLayout()
        self.left_layout1.setObjectName(u"left_layout1")
        self.image_container = QWidget(self.tab1)
        self.image_container.setObjectName(u"image_container")
        self.image_container.setMinimumSize(QSize(600, 500))
        self.container_layout1 = QGridLayout(self.image_container)
        self.container_layout1.setObjectName(u"container_layout1")
        self.container_layout1.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea(self.image_container)
        self.scroll_area.setObjectName(u"scroll_area")
        self.scroll_area.setStyleSheet(u"border: 1px solid gray;")
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_label = QLabel()
        self.image_label.setObjectName(u"image_label")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)

        self.container_layout1.addWidget(self.scroll_area, 0, 0, 1, 1)

        self.filename_label = QLabel(self.image_container)
        self.filename_label.setObjectName(u"filename_label")
        self.filename_label.setStyleSheet(u"background-color: rgba(0,0,0,150);\n"
"color: white;\n"
"padding: 2px 8px;\n"
"border-radius: 3px;\n"
"font-size: 12px;")
        self.filename_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.container_layout1.addWidget(self.filename_label, 0, 0, 1, 1, Qt.AlignRight|Qt.AlignTop)


        self.left_layout1.addWidget(self.image_container)


        self.content_layout1.addLayout(self.left_layout1)

        self.right_layout1 = QVBoxLayout()
        self.right_layout1.setObjectName(u"right_layout1")
        self.pid_filter_group1 = QGroupBox(self.tab1)
        self.pid_filter_group1.setObjectName(u"pid_filter_group1")
        self.pid_layout1 = QVBoxLayout(self.pid_filter_group1)
        self.pid_layout1.setObjectName(u"pid_layout1")
        self.pid_filter_checkbox = QCheckBox(self.pid_filter_group1)
        self.pid_filter_checkbox.setObjectName(u"pid_filter_checkbox")

        self.pid_layout1.addWidget(self.pid_filter_checkbox)

        self.model_identify_checkbox1 = QCheckBox(self.pid_filter_group1)
        self.model_identify_checkbox1.setObjectName(u"model_identify_checkbox1")

        self.pid_layout1.addWidget(self.model_identify_checkbox1)

        self.label_dl_mode1 = QLabel(self.pid_filter_group1)
        self.label_dl_mode1.setObjectName(u"label_dl_mode1")

        self.pid_layout1.addWidget(self.label_dl_mode1)

        self.dl_mode_combo1 = QComboBox(self.pid_filter_group1)
        self.dl_mode_combo1.addItem("")
        self.dl_mode_combo1.addItem("")
        self.dl_mode_combo1.addItem("")
        self.dl_mode_combo1.setObjectName(u"dl_mode_combo1")

        self.pid_layout1.addWidget(self.dl_mode_combo1)

        self.dl_spin1 = QSpinBox(self.pid_filter_group1)
        self.dl_spin1.setObjectName(u"dl_spin1")
        self.dl_spin1.setMinimum(1)
        self.dl_spin1.setMaximum(20)
        self.dl_spin1.setValue(1)

        self.pid_layout1.addWidget(self.dl_spin1)


        self.right_layout1.addWidget(self.pid_filter_group1)

        self.info_group1 = QGroupBox(self.tab1)
        self.info_group1.setObjectName(u"info_group1")
        self.info_layout1 = QVBoxLayout(self.info_group1)
        self.info_layout1.setObjectName(u"info_layout1")
        self.info_box = QTextEdit(self.info_group1)
        self.info_box.setObjectName(u"info_box")
        self.info_box.setMaximumSize(QSize(16777215, 150))
        self.info_box.setReadOnly(True)

        self.info_layout1.addWidget(self.info_box)

        self.stop_btn = QPushButton(self.info_group1)
        self.stop_btn.setObjectName(u"stop_btn")
        self.stop_btn.setStyleSheet(u"background-color: #dc3545; color: white;")
        self.stop_btn.setVisible(False)

        self.info_layout1.addWidget(self.stop_btn)


        self.right_layout1.addWidget(self.info_group1)

        self.right_spacer1 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.right_layout1.addItem(self.right_spacer1)


        self.content_layout1.addLayout(self.right_layout1)


        self.tab1_layout.addLayout(self.content_layout1)

        self.button_layout1 = QHBoxLayout()
        self.button_layout1.setObjectName(u"button_layout1")
        self.search_btn = QPushButton(self.tab1)
        self.search_btn.setObjectName(u"search_btn")
        self.search_btn.setStyleSheet(u"background-color: #0084ff; color: white;")

        self.button_layout1.addWidget(self.search_btn)

        self.prev_btn = QPushButton(self.tab1)
        self.prev_btn.setObjectName(u"prev_btn")
        self.prev_btn.setStyleSheet(u"background-color: #6c757d; color: white;")

        self.button_layout1.addWidget(self.prev_btn)

        self.next_btn = QPushButton(self.tab1)
        self.next_btn.setObjectName(u"next_btn")
        self.next_btn.setStyleSheet(u"background-color: #6c757d; color: white;")

        self.button_layout1.addWidget(self.next_btn)

        self.save_btn = QPushButton(self.tab1)
        self.save_btn.setObjectName(u"save_btn")
        self.save_btn.setStyleSheet(u"background-color: #28a745; color: white;")

        self.button_layout1.addWidget(self.save_btn)


        self.tab1_layout.addLayout(self.button_layout1)

        self.stack.addWidget(self.tab1)
        self.tab2 = QWidget()
        self.tab2.setObjectName(u"tab2")
        self.tab2_layout = QVBoxLayout(self.tab2)
        self.tab2_layout.setObjectName(u"tab2_layout")
        self.content_layout2 = QHBoxLayout()
        self.content_layout2.setObjectName(u"content_layout2")
        self.left_layout2 = QVBoxLayout()
        self.left_layout2.setObjectName(u"left_layout2")
        self.image_container2 = QWidget(self.tab2)
        self.image_container2.setObjectName(u"image_container2")
        self.image_container2.setMinimumSize(QSize(600, 500))
        self.container_layout2 = QGridLayout(self.image_container2)
        self.container_layout2.setObjectName(u"container_layout2")
        self.container_layout2.setContentsMargins(0, 0, 0, 0)
        self.scroll_area2 = QScrollArea(self.image_container2)
        self.scroll_area2.setObjectName(u"scroll_area2")
        self.scroll_area2.setStyleSheet(u"border: 1px solid gray;")
        self.scroll_area2.setWidgetResizable(False)
        self.scroll_area2.setAlignment(Qt.AlignCenter)
        self.scroll_area2.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area2.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_label2 = QLabel()
        self.image_label2.setObjectName(u"image_label2")
        self.image_label2.setAlignment(Qt.AlignCenter)
        self.scroll_area2.setWidget(self.image_label2)

        self.container_layout2.addWidget(self.scroll_area2, 0, 0, 1, 1)

        self.filename_label2 = QLabel(self.image_container2)
        self.filename_label2.setObjectName(u"filename_label2")
        self.filename_label2.setStyleSheet(u"background-color: rgba(0,0,0,150);\n"
"color: white;\n"
"padding: 2px 8px;\n"
"border-radius: 3px;\n"
"font-size: 12px;")
        self.filename_label2.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.container_layout2.addWidget(self.filename_label2, 0, 0, 1, 1, Qt.AlignRight|Qt.AlignTop)


        self.left_layout2.addWidget(self.image_container2)


        self.content_layout2.addLayout(self.left_layout2)

        self.right_layout2 = QVBoxLayout()
        self.right_layout2.setObjectName(u"right_layout2")
        self.search_setting_group2 = QGroupBox(self.tab2)
        self.search_setting_group2.setObjectName(u"search_setting_group2")
        self.search_content_layout2 = QVBoxLayout(self.search_setting_group2)
        self.search_content_layout2.setObjectName(u"search_content_layout2")
        self.label_search_content2 = QLabel(self.search_setting_group2)
        self.label_search_content2.setObjectName(u"label_search_content2")

        self.search_content_layout2.addWidget(self.label_search_content2)

        self.search_box2 = QComboBox(self.search_setting_group2)
        self.search_box2.addItem("")
        self.search_box2.addItem("")
        self.search_box2.addItem("")
        self.search_box2.setObjectName(u"search_box2")

        self.search_content_layout2.addWidget(self.search_box2)


        self.right_layout2.addWidget(self.search_setting_group2)

        self.filter_group2 = QGroupBox(self.tab2)
        self.filter_group2.setObjectName(u"filter_group2")
        self.filter_layout2 = QVBoxLayout(self.filter_group2)
        self.filter_layout2.setObjectName(u"filter_layout2")
        self.label_filter2 = QLabel(self.filter_group2)
        self.label_filter2.setObjectName(u"label_filter2")

        self.filter_layout2.addWidget(self.label_filter2)

        self.pid_filter_checkbox2 = QCheckBox(self.filter_group2)
        self.pid_filter_checkbox2.setObjectName(u"pid_filter_checkbox2")

        self.filter_layout2.addWidget(self.pid_filter_checkbox2)

        self.r18_checkbox2 = QCheckBox(self.filter_group2)
        self.r18_checkbox2.setObjectName(u"r18_checkbox2")
        self.r18_checkbox2.setChecked(True)

        self.filter_layout2.addWidget(self.r18_checkbox2)

        self.r18g_checkbox2 = QCheckBox(self.filter_group2)
        self.r18g_checkbox2.setObjectName(u"r18g_checkbox2")
        self.r18g_checkbox2.setChecked(True)

        self.filter_layout2.addWidget(self.r18g_checkbox2)

        self.r18_only_checkbox2 = QCheckBox(self.filter_group2)
        self.r18_only_checkbox2.setObjectName(u"r18_only_checkbox2")

        self.filter_layout2.addWidget(self.r18_only_checkbox2)

        self.label_dl_mode2 = QLabel(self.filter_group2)
        self.label_dl_mode2.setObjectName(u"label_dl_mode2")

        self.filter_layout2.addWidget(self.label_dl_mode2)

        self.dl_mode_combo2 = QComboBox(self.filter_group2)
        self.dl_mode_combo2.addItem("")
        self.dl_mode_combo2.addItem("")
        self.dl_mode_combo2.addItem("")
        self.dl_mode_combo2.setObjectName(u"dl_mode_combo2")

        self.filter_layout2.addWidget(self.dl_mode_combo2)

        self.dl_spin2 = QSpinBox(self.filter_group2)
        self.dl_spin2.setObjectName(u"dl_spin2")
        self.dl_spin2.setMinimum(1)
        self.dl_spin2.setMaximum(20)
        self.dl_spin2.setValue(1)

        self.filter_layout2.addWidget(self.dl_spin2)

        self.model_identify_checkbox2 = QCheckBox(self.filter_group2)
        self.model_identify_checkbox2.setObjectName(u"model_identify_checkbox2")

        self.filter_layout2.addWidget(self.model_identify_checkbox2)


        self.right_layout2.addWidget(self.filter_group2)

        self.info_group2 = QGroupBox(self.tab2)
        self.info_group2.setObjectName(u"info_group2")
        self.info_layout2 = QVBoxLayout(self.info_group2)
        self.info_layout2.setObjectName(u"info_layout2")
        self.info_box2 = QTextEdit(self.info_group2)
        self.info_box2.setObjectName(u"info_box2")
        self.info_box2.setMaximumSize(QSize(16777215, 150))
        self.info_box2.setReadOnly(True)

        self.info_layout2.addWidget(self.info_box2)

        self.stop_btn2 = QPushButton(self.info_group2)
        self.stop_btn2.setObjectName(u"stop_btn2")
        self.stop_btn2.setStyleSheet(u"background-color: #dc3545; color: white;")
        self.stop_btn2.setVisible(False)

        self.info_layout2.addWidget(self.stop_btn2)


        self.right_layout2.addWidget(self.info_group2)

        self.right_spacer2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.right_layout2.addItem(self.right_spacer2)


        self.content_layout2.addLayout(self.right_layout2)


        self.tab2_layout.addLayout(self.content_layout2)

        self.button_layout2 = QHBoxLayout()
        self.button_layout2.setObjectName(u"button_layout2")
        self.search_btn2 = QPushButton(self.tab2)
        self.search_btn2.setObjectName(u"search_btn2")
        self.search_btn2.setStyleSheet(u"background-color: #0084ff; color: white;")

        self.button_layout2.addWidget(self.search_btn2)

        self.prev_btn2 = QPushButton(self.tab2)
        self.prev_btn2.setObjectName(u"prev_btn2")
        self.prev_btn2.setStyleSheet(u"background-color: #6c757d; color: white;")

        self.button_layout2.addWidget(self.prev_btn2)

        self.next_btn2 = QPushButton(self.tab2)
        self.next_btn2.setObjectName(u"next_btn2")
        self.next_btn2.setStyleSheet(u"background-color: #6c757d; color: white;")

        self.button_layout2.addWidget(self.next_btn2)

        self.save_btn2 = QPushButton(self.tab2)
        self.save_btn2.setObjectName(u"save_btn2")
        self.save_btn2.setStyleSheet(u"background-color: #28a745; color: white;")

        self.button_layout2.addWidget(self.save_btn2)


        self.tab2_layout.addLayout(self.button_layout2)

        self.stack.addWidget(self.tab2)
        self.tab3 = QWidget()
        self.tab3.setObjectName(u"tab3")
        self.tab3_layout = QVBoxLayout(self.tab3)
        self.tab3_layout.setObjectName(u"tab3_layout")
        self.search_group3 = QGroupBox(self.tab3)
        self.search_group3.setObjectName(u"search_group3")
        self.search_layout3 = QGridLayout(self.search_group3)
        self.search_layout3.setObjectName(u"search_layout3")
        self.label_author_id = QLabel(self.search_group3)
        self.label_author_id.setObjectName(u"label_author_id")

        self.search_layout3.addWidget(self.label_author_id, 0, 0, 1, 1)

        self.author_id_input = QLineEdit(self.search_group3)
        self.author_id_input.setObjectName(u"author_id_input")

        self.search_layout3.addWidget(self.author_id_input, 0, 1, 1, 1)


        self.tab3_layout.addWidget(self.search_group3)

        self.content_layout3 = QHBoxLayout()
        self.content_layout3.setObjectName(u"content_layout3")
        self.left_layout3 = QVBoxLayout()
        self.left_layout3.setObjectName(u"left_layout3")
        self.image_container3 = QWidget(self.tab3)
        self.image_container3.setObjectName(u"image_container3")
        self.image_container3.setMinimumSize(QSize(600, 500))
        self.container_layout3 = QGridLayout(self.image_container3)
        self.container_layout3.setObjectName(u"container_layout3")
        self.container_layout3.setContentsMargins(0, 0, 0, 0)
        self.scroll_area3 = QScrollArea(self.image_container3)
        self.scroll_area3.setObjectName(u"scroll_area3")
        self.scroll_area3.setStyleSheet(u"border: 1px solid gray;")
        self.scroll_area3.setWidgetResizable(False)
        self.scroll_area3.setAlignment(Qt.AlignCenter)
        self.scroll_area3.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area3.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_label3 = QLabel()
        self.image_label3.setObjectName(u"image_label3")
        self.image_label3.setAlignment(Qt.AlignCenter)
        self.scroll_area3.setWidget(self.image_label3)

        self.container_layout3.addWidget(self.scroll_area3, 0, 0, 1, 1)

        self.filename_label3 = QLabel(self.image_container3)
        self.filename_label3.setObjectName(u"filename_label3")
        self.filename_label3.setStyleSheet(u"background-color: rgba(0,0,0,150);\n"
"color: white;\n"
"padding: 2px 8px;\n"
"border-radius: 3px;\n"
"font-size: 12px;")
        self.filename_label3.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.container_layout3.addWidget(self.filename_label3, 0, 0, 1, 1, Qt.AlignRight|Qt.AlignTop)


        self.left_layout3.addWidget(self.image_container3)


        self.content_layout3.addLayout(self.left_layout3)

        self.right_layout3 = QVBoxLayout()
        self.right_layout3.setObjectName(u"right_layout3")
        self.option_group3 = QGroupBox(self.tab3)
        self.option_group3.setObjectName(u"option_group3")
        self.option_layout3 = QVBoxLayout(self.option_group3)
        self.option_layout3.setObjectName(u"option_layout3")
        self.pid_filter_checkbox3 = QCheckBox(self.option_group3)
        self.pid_filter_checkbox3.setObjectName(u"pid_filter_checkbox3")

        self.option_layout3.addWidget(self.pid_filter_checkbox3)

        self.r18_checkbox3 = QCheckBox(self.option_group3)
        self.r18_checkbox3.setObjectName(u"r18_checkbox3")
        self.r18_checkbox3.setChecked(True)

        self.option_layout3.addWidget(self.r18_checkbox3)

        self.r18g_checkbox3 = QCheckBox(self.option_group3)
        self.r18g_checkbox3.setObjectName(u"r18g_checkbox3")
        self.r18g_checkbox3.setChecked(True)

        self.option_layout3.addWidget(self.r18g_checkbox3)

        self.r18_only_checkbox3 = QCheckBox(self.option_group3)
        self.r18_only_checkbox3.setObjectName(u"r18_only_checkbox3")

        self.option_layout3.addWidget(self.r18_only_checkbox3)

        self.model_identify_checkbox3 = QCheckBox(self.option_group3)
        self.model_identify_checkbox3.setObjectName(u"model_identify_checkbox3")

        self.option_layout3.addWidget(self.model_identify_checkbox3)


        self.right_layout3.addWidget(self.option_group3)

        self.info_group3 = QGroupBox(self.tab3)
        self.info_group3.setObjectName(u"info_group3")
        self.info_layout3 = QVBoxLayout(self.info_group3)
        self.info_layout3.setObjectName(u"info_layout3")
        self.info_box3 = QTextEdit(self.info_group3)
        self.info_box3.setObjectName(u"info_box3")
        self.info_box3.setMaximumSize(QSize(16777215, 150))
        self.info_box3.setReadOnly(True)

        self.info_layout3.addWidget(self.info_box3)

        self.stop_btn3 = QPushButton(self.info_group3)
        self.stop_btn3.setObjectName(u"stop_btn3")
        self.stop_btn3.setStyleSheet(u"background-color: #dc3545; color: white;")
        self.stop_btn3.setVisible(False)

        self.info_layout3.addWidget(self.stop_btn3)


        self.right_layout3.addWidget(self.info_group3)

        self.right_spacer3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.right_layout3.addItem(self.right_spacer3)


        self.content_layout3.addLayout(self.right_layout3)


        self.tab3_layout.addLayout(self.content_layout3)

        self.button_layout3 = QHBoxLayout()
        self.button_layout3.setObjectName(u"button_layout3")
        self.search_btn3 = QPushButton(self.tab3)
        self.search_btn3.setObjectName(u"search_btn3")
        self.search_btn3.setStyleSheet(u"background-color: #0084ff; color: white;")

        self.button_layout3.addWidget(self.search_btn3)

        self.prev_btn3 = QPushButton(self.tab3)
        self.prev_btn3.setObjectName(u"prev_btn3")
        self.prev_btn3.setStyleSheet(u"background-color: #6c757d; color: white;")

        self.button_layout3.addWidget(self.prev_btn3)

        self.next_btn3 = QPushButton(self.tab3)
        self.next_btn3.setObjectName(u"next_btn3")
        self.next_btn3.setStyleSheet(u"background-color: #6c757d; color: white;")

        self.button_layout3.addWidget(self.next_btn3)

        self.save_btn3 = QPushButton(self.tab3)
        self.save_btn3.setObjectName(u"save_btn3")
        self.save_btn3.setStyleSheet(u"background-color: #28a745; color: white;")

        self.button_layout3.addWidget(self.save_btn3)


        self.tab3_layout.addLayout(self.button_layout3)

        self.stack.addWidget(self.tab3)
        self.tab4 = QWidget()
        self.tab4.setObjectName(u"tab4")
        self.tab4_layout = QVBoxLayout(self.tab4)
        self.tab4_layout.setObjectName(u"tab4_layout")
        self.settings_title = QLabel(self.tab4)
        self.settings_title.setObjectName(u"settings_title")
        self.settings_title.setStyleSheet(u"font-size: 18px; font-weight: bold; padding: 10px;")

        self.tab4_layout.addWidget(self.settings_title)

        self.php_group = QGroupBox(self.tab4)
        self.php_group.setObjectName(u"php_group")
        self.php_group_layout = QVBoxLayout(self.php_group)
        self.php_group_layout.setObjectName(u"php_group_layout")
        self.php_row = QHBoxLayout()
        self.php_row.setObjectName(u"php_row")
        self.label_php = QLabel(self.php_group)
        self.label_php.setObjectName(u"label_php")

        self.php_row.addWidget(self.label_php)

        self.php_input_global = QLineEdit(self.php_group)
        self.php_input_global.setObjectName(u"php_input_global")

        self.php_row.addWidget(self.php_input_global)

        self.get_php_btn = QPushButton(self.php_group)
        self.get_php_btn.setObjectName(u"get_php_btn")

        self.php_row.addWidget(self.get_php_btn)

        self.check_php_btn = QPushButton(self.php_group)
        self.check_php_btn.setObjectName(u"check_php_btn")

        self.php_row.addWidget(self.check_php_btn)


        self.php_group_layout.addLayout(self.php_row)

        self.php_status_label = QLabel(self.php_group)
        self.php_status_label.setObjectName(u"php_status_label")
        self.php_status_label.setStyleSheet(u"padding: 4px;")

        self.php_group_layout.addWidget(self.php_status_label)


        self.tab4_layout.addWidget(self.php_group)

        self.model_group = QGroupBox(self.tab4)
        self.model_group.setObjectName(u"model_group")
        self.model_group_layout = QVBoxLayout(self.model_group)
        self.model_group_layout.setObjectName(u"model_group_layout")
        self.model_row = QHBoxLayout()
        self.model_row.setObjectName(u"model_row")
        self.label_model = QLabel(self.model_group)
        self.label_model.setObjectName(u"label_model")

        self.model_row.addWidget(self.label_model)

        self.model_combo = QComboBox(self.model_group)
        self.model_combo.setObjectName(u"model_combo")

        self.model_row.addWidget(self.model_combo)

        self.browse_model_btn = QPushButton(self.model_group)
        self.browse_model_btn.setObjectName(u"browse_model_btn")

        self.model_row.addWidget(self.browse_model_btn)


        self.model_group_layout.addLayout(self.model_row)

        self.model_status_label = QLabel(self.model_group)
        self.model_status_label.setObjectName(u"model_status_label")
        self.model_status_label.setStyleSheet(u"padding: 4px; color: gray;")

        self.model_group_layout.addWidget(self.model_status_label)


        self.tab4_layout.addWidget(self.model_group)

        self.page_limit_group = QGroupBox(self.tab4)
        self.page_limit_group.setObjectName(u"page_limit_group")
        self.page_limit_layout = QVBoxLayout(self.page_limit_group)
        self.page_limit_layout.setObjectName(u"page_limit_layout")
        self.page_limit_row = QHBoxLayout()
        self.page_limit_row.setObjectName(u"page_limit_row")
        self.page_limit_checkbox = QCheckBox(self.page_limit_group)
        self.page_limit_checkbox.setObjectName(u"page_limit_checkbox")

        self.page_limit_row.addWidget(self.page_limit_checkbox)

        self.page_limit_spin = QSpinBox(self.page_limit_group)
        self.page_limit_spin.setObjectName(u"page_limit_spin")
        self.page_limit_spin.setEnabled(False)
        self.page_limit_spin.setMinimum(1)
        self.page_limit_spin.setMaximum(100)
        self.page_limit_spin.setValue(20)

        self.page_limit_row.addWidget(self.page_limit_spin)

        self.label_page_limit_tail = QLabel(self.page_limit_group)
        self.label_page_limit_tail.setObjectName(u"label_page_limit_tail")

        self.page_limit_row.addWidget(self.label_page_limit_tail)


        self.page_limit_layout.addLayout(self.page_limit_row)


        self.tab4_layout.addWidget(self.page_limit_group)

        self.bg_group = QGroupBox(self.tab4)
        self.bg_group.setObjectName(u"bg_group")
        self.bg_layout = QVBoxLayout(self.bg_group)
        self.bg_layout.setObjectName(u"bg_layout")
        self.bg_row = QHBoxLayout()
        self.bg_row.setObjectName(u"bg_row")
        self.label_bg_image = QLabel(self.bg_group)
        self.label_bg_image.setObjectName(u"label_bg_image")

        self.bg_row.addWidget(self.label_bg_image)

        self.bg_image_combo = QComboBox(self.bg_group)
        self.bg_image_combo.setObjectName(u"bg_image_combo")
        self.bg_image_combo.setMinimumSize(QSize(200, 0))

        self.bg_row.addWidget(self.bg_image_combo)

        self.set_bg_image_btn = QPushButton(self.bg_group)
        self.set_bg_image_btn.setObjectName(u"set_bg_image_btn")

        self.bg_row.addWidget(self.set_bg_image_btn)

        self.delete_bg_image_btn = QPushButton(self.bg_group)
        self.delete_bg_image_btn.setObjectName(u"delete_bg_image_btn")

        self.bg_row.addWidget(self.delete_bg_image_btn)

        self.browse_bg_image_btn = QPushButton(self.bg_group)
        self.browse_bg_image_btn.setObjectName(u"browse_bg_image_btn")

        self.bg_row.addWidget(self.browse_bg_image_btn)


        self.bg_layout.addLayout(self.bg_row)

        self.opacity_row = QHBoxLayout()
        self.opacity_row.setObjectName(u"opacity_row")
        self.label_opacity = QLabel(self.bg_group)
        self.label_opacity.setObjectName(u"label_opacity")

        self.opacity_row.addWidget(self.label_opacity)

        self.opacity_slider = QSlider(self.bg_group)
        self.opacity_slider.setObjectName(u"opacity_slider")
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(0)
        self.opacity_slider.setOrientation(Qt.Horizontal)

        self.opacity_row.addWidget(self.opacity_slider)

        self.opacity_value_label = QLabel(self.bg_group)
        self.opacity_value_label.setObjectName(u"opacity_value_label")
        self.opacity_value_label.setMinimumSize(QSize(44, 0))
        self.opacity_value_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.opacity_row.addWidget(self.opacity_value_label)


        self.bg_layout.addLayout(self.opacity_row)

        self.bg_status_label = QLabel(self.bg_group)
        self.bg_status_label.setObjectName(u"bg_status_label")
        self.bg_status_label.setStyleSheet(u"padding: 4px; color: gray;")

        self.bg_layout.addWidget(self.bg_status_label)


        self.tab4_layout.addWidget(self.bg_group)

        self.cache_group = QGroupBox(self.tab4)
        self.cache_group.setObjectName(u"cache_group")
        self.cache_layout = QHBoxLayout(self.cache_group)
        self.cache_layout.setObjectName(u"cache_layout")
        self.label_cache = QLabel(self.cache_group)
        self.label_cache.setObjectName(u"label_cache")

        self.cache_layout.addWidget(self.label_cache)

        self.cache_size_label = QLabel(self.cache_group)
        self.cache_size_label.setObjectName(u"cache_size_label")

        self.cache_layout.addWidget(self.cache_size_label)

        self.cache_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.cache_layout.addItem(self.cache_spacer)

        self.clear_cache_btn = QPushButton(self.cache_group)
        self.clear_cache_btn.setObjectName(u"clear_cache_btn")

        self.cache_layout.addWidget(self.clear_cache_btn)


        self.tab4_layout.addWidget(self.cache_group)

        self.tab4_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.tab4_layout.addItem(self.tab4_spacer)

        self.stack.addWidget(self.tab4)

        self.main_layout.addWidget(self.stack)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Pixiv \u56fe\u7247\u7b5b\u9009\u5668", None))
        self.tab_btn1.setText(QCoreApplication.translate("MainWindow", u"\u7b5b\u9009\u5668", None))
        self.tab_btn2.setText(QCoreApplication.translate("MainWindow", u"\u7eb3\u897f\u59b2", None))
        self.tab_btn3.setText(QCoreApplication.translate("MainWindow", u"\u4f5c\u8005\u4f5c\u54c1", None))
        self.tab_btn4.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e", None))
        self.search_group1.setTitle("")
        self.label_keywords.setText(QCoreApplication.translate("MainWindow", u"\u641c\u7d22\u5173\u952e\u8bcd:", None))
        self.label_filter.setText(QCoreApplication.translate("MainWindow", u"\u5185\u5bb9\u8fc7\u6ee4:", None))
        self.r18_checkbox.setText(QCoreApplication.translate("MainWindow", u"R18\u8fc7\u6ee4", None))
        self.r18g_checkbox.setText(QCoreApplication.translate("MainWindow", u"R18G\u8fc7\u6ee4", None))
        self.r18_only_checkbox.setText(QCoreApplication.translate("MainWindow", u"\u4ec5R18\u5185\u5bb9", None))
        self.image_label.setText("")
        self.filename_label.setText("")
        self.pid_filter_group1.setTitle("")
        self.pid_filter_checkbox.setText(QCoreApplication.translate("MainWindow", u"pid\u5c4f\u853d", None))
        self.model_identify_checkbox1.setText(QCoreApplication.translate("MainWindow", u"\u6a21\u578b\u8bc6\u522b", None))
        self.label_dl_mode1.setText(QCoreApplication.translate("MainWindow", u"\u4e0b\u8f7d\u65b9\u5f0f:", None))
        self.dl_mode_combo1.setItemText(0, QCoreApplication.translate("MainWindow", u"\u9875\u6570\u6a21\u5f0f", None))
        self.dl_mode_combo1.setItemText(1, QCoreApplication.translate("MainWindow", u"\u56fe\u7247\u5f20\u6570", None))
        self.dl_mode_combo1.setItemText(2, QCoreApplication.translate("MainWindow", u"PID\u4e2a\u6570", None))

        self.info_group1.setTitle("")
        self.stop_btn.setText(QCoreApplication.translate("MainWindow", u"\u23f9 \u505c\u6b62", None))
        self.search_btn.setText(QCoreApplication.translate("MainWindow", u"\U0001f50d \U0000641c\U00007d22", None))
        self.prev_btn.setText(QCoreApplication.translate("MainWindow", u"\u2b05 \u4e0a\u4e00\u5f20", None))
        self.next_btn.setText(QCoreApplication.translate("MainWindow", u"\u4e0b\u4e00\u5f20 \u27a1", None))
        self.save_btn.setText(QCoreApplication.translate("MainWindow", u"\u2705 \u4fdd\u5b58", None))
        self.image_label2.setText("")
        self.filename_label2.setText("")
        self.search_setting_group2.setTitle("")
        self.label_search_content2.setText(QCoreApplication.translate("MainWindow", u"\u641c\u7d22\u5185\u5bb9:", None))
        self.search_box2.setItemText(0, QCoreApplication.translate("MainWindow", u"nahida", None))
        self.search_box2.setItemText(1, QCoreApplication.translate("MainWindow", u"\u7eb3\u897f\u59b2", None))
        self.search_box2.setItemText(2, QCoreApplication.translate("MainWindow", u"\u30ca\u30d2\u30fc\u30c0", None))

        self.filter_group2.setTitle("")
        self.label_filter2.setText(QCoreApplication.translate("MainWindow", u"\u8fc7\u6ee4\u9009\u9879:", None))
        self.pid_filter_checkbox2.setText(QCoreApplication.translate("MainWindow", u"pid\u5c4f\u853d", None))
        self.r18_checkbox2.setText(QCoreApplication.translate("MainWindow", u"R18\u8fc7\u6ee4", None))
        self.r18g_checkbox2.setText(QCoreApplication.translate("MainWindow", u"R18G\u8fc7\u6ee4", None))
        self.r18_only_checkbox2.setText(QCoreApplication.translate("MainWindow", u"\u4ec5R18\u5185\u5bb9", None))
        self.label_dl_mode2.setText(QCoreApplication.translate("MainWindow", u"\u4e0b\u8f7d\u65b9\u5f0f:", None))
        self.dl_mode_combo2.setItemText(0, QCoreApplication.translate("MainWindow", u"\u9875\u6570\u6a21\u5f0f", None))
        self.dl_mode_combo2.setItemText(1, QCoreApplication.translate("MainWindow", u"\u56fe\u7247\u5f20\u6570", None))
        self.dl_mode_combo2.setItemText(2, QCoreApplication.translate("MainWindow", u"PID\u4e2a\u6570", None))

        self.model_identify_checkbox2.setText(QCoreApplication.translate("MainWindow", u"\u6a21\u578b\u8bc6\u522b", None))
        self.info_group2.setTitle("")
        self.stop_btn2.setText(QCoreApplication.translate("MainWindow", u"\u23f9 \u505c\u6b62", None))
        self.search_btn2.setText(QCoreApplication.translate("MainWindow", u"\U0001f50d \U0000641c\U00007d22", None))
        self.prev_btn2.setText(QCoreApplication.translate("MainWindow", u"\u2b05 \u4e0a\u4e00\u5f20", None))
        self.next_btn2.setText(QCoreApplication.translate("MainWindow", u"\u4e0b\u4e00\u5f20 \u27a1", None))
        self.save_btn2.setText(QCoreApplication.translate("MainWindow", u"\u2705 \u4fdd\u5b58", None))
        self.search_group3.setTitle("")
        self.label_author_id.setText(QCoreApplication.translate("MainWindow", u"\u4f5c\u8005ID:", None))
        self.image_label3.setText("")
        self.filename_label3.setText("")
        self.option_group3.setTitle("")
        self.pid_filter_checkbox3.setText(QCoreApplication.translate("MainWindow", u"pid\u5c4f\u853d", None))
        self.r18_checkbox3.setText(QCoreApplication.translate("MainWindow", u"R18\u8fc7\u6ee4", None))
        self.r18g_checkbox3.setText(QCoreApplication.translate("MainWindow", u"R18G\u8fc7\u6ee4", None))
        self.r18_only_checkbox3.setText(QCoreApplication.translate("MainWindow", u"\u4ec5R18\u5185\u5bb9", None))
        self.model_identify_checkbox3.setText(QCoreApplication.translate("MainWindow", u"\u6a21\u578b\u8bc6\u522b", None))
        self.info_group3.setTitle("")
        self.stop_btn3.setText(QCoreApplication.translate("MainWindow", u"\u23f9 \u505c\u6b62", None))
        self.search_btn3.setText(QCoreApplication.translate("MainWindow", u"\U0001f50d \U0000641c\U00007d22", None))
        self.prev_btn3.setText(QCoreApplication.translate("MainWindow", u"\u2b05 \u4e0a\u4e00\u5f20", None))
        self.next_btn3.setText(QCoreApplication.translate("MainWindow", u"\u4e0b\u4e00\u5f20 \u27a1", None))
        self.save_btn3.setText(QCoreApplication.translate("MainWindow", u"\u2705 \u4fdd\u5b58", None))
        self.settings_title.setText(QCoreApplication.translate("MainWindow", u"\u2699 \u8bbe\u7f6e", None))
        self.php_group.setTitle("")
        self.label_php.setText(QCoreApplication.translate("MainWindow", u"PHPSESSID:", None))
        self.get_php_btn.setText(QCoreApplication.translate("MainWindow", u"\u83b7\u53d6", None))
        self.check_php_btn.setText(QCoreApplication.translate("MainWindow", u"\u68c0\u6d4b", None))
        self.php_status_label.setText("")
        self.model_group.setTitle("")
        self.label_model.setText(QCoreApplication.translate("MainWindow", u"\u6a21\u578b\u9009\u62e9(ONNX):", None))
        self.browse_model_btn.setText(QCoreApplication.translate("MainWindow", u"\u6d4f\u89c8\u76ee\u5f55", None))
        self.model_status_label.setText("")
        self.page_limit_group.setTitle("")
        self.page_limit_checkbox.setText(QCoreApplication.translate("MainWindow", u"PID\u5185\u8d85\u8fc7", None))
        self.label_page_limit_tail.setText(QCoreApplication.translate("MainWindow", u"\u5f20\u5219\u8df3\u8fc7\u8be5PID", None))
        self.bg_group.setTitle("")
        self.label_bg_image.setText(QCoreApplication.translate("MainWindow", u"\u80cc\u666f\u56fe:", None))
        self.set_bg_image_btn.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e", None))
        self.delete_bg_image_btn.setText(QCoreApplication.translate("MainWindow", u"\u5220\u9664", None))
        self.browse_bg_image_btn.setText(QCoreApplication.translate("MainWindow", u"\u6dfb\u52a0", None))
        self.label_opacity.setText(QCoreApplication.translate("MainWindow", u"\u5b50\u63a7\u4ef6\u900f\u660e\u5ea6:", None))
        self.opacity_value_label.setText(QCoreApplication.translate("MainWindow", u"0%", None))
        self.bg_status_label.setText("")
        self.cache_group.setTitle("")
        self.label_cache.setText(QCoreApplication.translate("MainWindow", u"\u7f13\u5b58\u5927\u5c0f:", None))
        self.cache_size_label.setText(QCoreApplication.translate("MainWindow", u"0 B", None))
        self.clear_cache_btn.setText(QCoreApplication.translate("MainWindow", u"\u6e05\u7406\u7f13\u5b58", None))
    # retranslateUi

