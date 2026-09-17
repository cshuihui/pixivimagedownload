# Pixiv 图片筛选器

基于 **PySide6** 的 Pixiv 图片下载与筛选桌面工具，支持关键词 / 作者 / PID 三种搜索方式、R18/R18G 过滤、AI 模型识别筛选、图片预览与管理。

## 功能特性

- 🔍 **关键词搜索** — 按关键词搜索 Pixiv 作品，支持多页批量获取
- 🖼 **图片预览** — PySide6 桌面 GUI，支持**滚轮缩放** + **鼠标拖拽**浏览大图
- 🚫 **R18 / R18G 过滤** — 可选择屏蔽或仅保留 R18 内容
- 🤖 **AI 模型识别** — 妲厨专用，内置 CNN 卷积神经网络（NahidaCNN），自动识别图片是否为"纳西妲"
- 📥 **批量下载** — 支持多页、多 PID、多页数限制下载，带暂停/停止控制
- 📋 **PID 黑名单** — 手动屏蔽不需要的作品 ID，避免重复出现
- 🔐 **PHPSESSID 自动获取** — 通过 Selenium 自动登录并提取 Cookie
- 👤 **作者作品** — 按画师批量获取其全部作品
- 🎯 **PID 直查** — 直接输入作品 ID 下载
- 📦 **一键打包** — `python build.py --release` 打包为免安装 exe

## 项目结构

```
├── main.py                  # 主程序入口 — PySide6 桌面 GUI
├── main_window.ui           # 界面源文件（Qt Designer）
├── ui/                      # 界面层
│   ├── main_window.py       # PixivFilterApp 主窗口（布局 + 事件/信号槽）
│   ├── ui_main_window.py    # 由 main_window.ui 生成（pyside6-uic），请勿手改
│   └── app.qss              # 全局样式表
├── workers/                 # 后台任务（QObject + QThread）
│   ├── search_worker.py     # 关键词 / 作者 / PID 搜索与下载
│   ├── save_worker.py       # 保存原图
│   └── php_worker.py        # PHPSESSID 获取 / 检测
├── logic/                   # 业务逻辑与配置
│   ├── image_logic.py       # 图片 / 文件名逻辑 + PID 黑名单
│   └── config_logic.py      # 路径、启动初始化、config.json 读写
├── build.py                 # 打包脚本 (PyInstaller)
├── pixiv_image_download.py  # 图片下载模块
├── pixiv_imagelink.py       # Pixiv 直链获取模块
├── pixiv_id.py              # 作品 ID 搜索模块
├── get_phpsessid.py         # PHPSESSID 自动获取 (Selenium)
├── instal_webdriver_manager.py  # Edge WebDriver 安装
├── model_script/            # AI 模型模块
│   ├── param.py             # 模型定义 (NahidaCNN)
│   ├── train.py             # 模型训练脚本
│   ├── predict.py           # PyTorch 推理
│   └── function.py          # ONNX 转换 & 推理
├── models/                  # 预训练模型（发布用 .onnx）
├── theme/                   # 预设背景图
├── requirements.txt         # Python 依赖
├── config/config.json       # 设置：背景图 / 透明度 / PHPSESSID（首次运行生成）
└── pids_filter.txt          # PID 黑名单（首次运行生成，初始为空）
```

> `datasets/pic_datasets/`（训练数据）与 `models/*.pth`（PyTorch 权重）仅供本地训练，
> 不随仓库分发 —— 用户端只需要 `models/*.onnx`。

## 快速开始

### 1. 环境要求

- Python 3.11+
- 需要自备网络代理工具（访问 Pixiv 所需）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 PHPSESSID

打开程序「设置 → PHPSESSID」：粘贴后点「检测」，通过会写入 `config/config.json`；
或点「获取」自动打开 Edge 跳转 Pixiv 登录页，登录后自动提取。

> 不再使用 `phpsessid.txt`（旧文件可自行删除）。

### 4. 运行

```bash
python main.py
```

### 5. 打包为 exe

```bash
python build.py --release        # 生成 release/Pixiv图片筛选器/
python build.py --release --zip  # 顺便压成 zip，便于分发
```

`--release` 会自动隐藏控制台、把 `models/` 与 `theme/` 放到 exe 同级、预建
`config/ saved/ temp/`，并在产物里生成 `使用说明.txt`。训练用的 `.pth` 权重不会被打进去。

## 使用说明

### 筛选器页面（Tab 1）

| 功能 | 说明 |
|------|------|
| 搜索关键词 | 输入 Pixiv 搜索标签（如 `ナヒーダ`） |
| 搜索页数 | 指定爬取页数（每页约 60 个作品） |
| R18/R18G 过滤 | 勾选后自动跳过对应类型的作品 |
| 仅 R18 内容 | 只保留 R18 作品（与前两者互斥） |
| 图片预览 | 滚轮缩放、鼠标拖拽移动视口 |
| 保存 | 将当前图片以原画质保存到 `saved/` 目录 |
| 丢弃 | 将当前 PID 加入黑名单，不再显示 |

### 纳西妲专页（Tab 2）

功能与筛选器相同，额外内置 **AI 模型识别**：自动筛选出包含"纳西妲"的图片。

### 作者作品（Tab 3）

输入画师名或主页，批量获取该画师的作品列表，之后的预览 / 保存 / 丢弃操作与筛选器页一致。

### PID 直查（Tab 4）

直接粘贴作品 ID 下载。此页不做 R18 过滤、也不检查 PID 黑名单 ——
用于已经明确知道要哪一张、不希望被过滤条件拦掉的场景。

### 设置页面（Tab 5）

- **下载限制**：按"图片张数"或"PID 个数"限制下载量
- **页码限制**：跳过页数过多的作品（如跳过超过 5 页的合辑）
- **模型识别**：启用/关闭 AI 识别功能
- **背景图 / 透明度**：从 `theme/default_image`、`theme/added_image` 选择背景图，并调整界面透明度
- **清理缓存**：清空 `temp/` 中的预览图缓存
- **PHPSESSID**：粘贴后点「检测」验证，或点「获取」自动抓取

## AI 模型

### NahidaCNN

自定义卷积神经网络，用于对 Pixiv 图片进行二分类：

- **类别 0**：非纳西妲
- **类别 1**：纳西妲（《原神》角色）

模型结构：3 层卷积 + 3 层全连接，输入尺寸 128×128。

### 模型格式

- `.pth` — PyTorch 权重文件（训练/开发用）
- `.onnx` — ONNX 格式（用户端部署用，无需安装 PyTorch）

### 训练

```bash
python -m model_script.train
```

训练数据放在 `datasets/pic_datasets/0/` 和 `datasets/pic_datasets/1/`。

### 转换为 ONNX

```bash
python -m model_script.function
```

## 依赖概览

| 包 | 用途 |
|------|------|
| PySide6 | 桌面 GUI 框架 |
| requests | Pixiv API 请求 |
| selenium | 自动获取 PHPSESSID |
| onnxruntime | 模型推理（用户端） |
| torch / torchvision | 模型训练（开发端） |
| numpy / pillow | 图像处理 |
| pyinstaller | 打包为 exe |

## 更新日志

### [260918] — 2026-09-18 · v0.1.0-beta.1（首个公开测试版）
- 整理为可公开发行的版本：清理个人配置、训练数据与未使用的 Gradio Web UI 入口
- 用户端改用 ONNX 推理，无需安装 PyTorch
- 五个页面：筛选器 / 纳西妲 / 作者作品 / PID / 设置
- 侧边栏新增「打开目录」按钮，直达下载文件夹
- 界面统一为圆角卡片样式；修复启动时背景图不显示的问题
- 下载按搜索关键词自动分二级目录
- PHPSESSID 改存 `config/config.json`，不再使用 `phpsessid.txt`
- `python build.py --release` 一键打包免安装 exe

### [251016] — 2025-10-16
- 增加 R18/R18G 标签筛选
- 优化多页作品下载逻辑

### [260405] — 2026-04-05
- 搭建 Gradio Web UI

### [260406] — 2026-04-06
- 优化下载逻辑和速度
- 新增 PID 屏蔽功能

### [260415] — 2026-04-15
- saved 目录增加二级目录（按搜索关键词分类）

### [260527] — 2026-05-27
- 添加纳西妲专用页
- 优化防反爬重试机制
- 预览使用低画质，下载使用原画质

## 注意事项

> ⚠️ 本工具仅供个人学习交流使用，请遵守 Pixiv 的使用条款。
> ⚠️ 请勿滥用，合理设置下载间隔，避免对 Pixiv 服务器造成压力。
> ⚠️ 开发端建议安装 CUDA 版 PyTorch 加速训练，用户端使用 ONNX 即可。
