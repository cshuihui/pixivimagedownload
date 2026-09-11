# -*- coding: utf-8 -*-
"""
logic/config_logic.py — 配置 / 路径 / 全局可变状态

从原 test_app.py 顶部与配置相关代码拆出：
- 资源/数据路径解析（resource_path / data_path）
- 默认图片查找（default_image）
- 各文件/目录常量（pids_filter / phpsessid / temp / saved / models / config）
- 启动初始化：目录创建、默认文件复制、临时目录清理、PHPSESSID 读取
- 可变全局状态：model_path
- config/config.json 的读写

⚠️ 第一阶段仅做代码拆分，行为与原 test_app.py 保持一致。
"""

import os
import shutil
import sys
import json


# ==================== 路径工具 ====================
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


# ==================== 路径 / 文件常量 ====================
default_image = _find_default_image()
pids_filter_dir = data_path('pids_filter.txt')
temp_dir = 'temp'
save_dir = 'saved'
model_dir = os.path.join(os.path.abspath("."), 'models')
model_path = os.path.join(model_dir, 'nahida_cnn_best.onnx')
config_dir = os.path.join(os.path.abspath("."), 'config')
config_file = os.path.join(config_dir, 'config.json')


# ==================== 启动初始化 ====================
# 确保目录存在（不再清空 temp；缓存清理改由「设置 → 清理缓存」手动执行）
os.makedirs(model_dir, exist_ok=True)
os.makedirs(save_dir, exist_ok=True)
os.makedirs(temp_dir, exist_ok=True)

# 读取 pids_filter.txt（优先当前目录，不存在则从打包目录复制默认文件）
if not os.path.exists(pids_filter_dir):
    src = resource_path('pids_filter.txt')
    if os.path.exists(src):
        shutil.copy2(src, pids_filter_dir)


# ==================== config/config.json 读写 ====================
CONFIG_KEYS = ('background_image', 'ui_transparency', 'phpsessid')


def load_ui_config():
    """读取 config/config.json（背景图 + 子控件透明度 + PHPSESSID）。

    返回 dict：{'background_image': str, 'ui_transparency': int, 'phpsessid': str}；
    文件不存在或读取异常时返回空 dict（由调用方取默认值）。
    """
    if not os.path.exists(config_file):
        return {}
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {k: data.get(k) for k in CONFIG_KEYS}
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return {}


def save_ui_config(background_image, ui_transparency, phpsessid=''):
    """把背景图、子控件透明度、PHPSESSID 写入 config/config.json（不存在则自动建目录）

    透明度：0 = 不透明，100 = 全透明。
    """
    os.makedirs(config_dir, exist_ok=True)
    try:
        data = {
            'background_image': background_image or '',
            'ui_transparency': int(ui_transparency),
            'phpsessid': phpsessid or '',
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置文件失败: {e}")


# PHPSESSID 现在保存在 config/config.json（不再使用 phpsessid.txt）
phpsessid = (load_ui_config().get('phpsessid') or '')
