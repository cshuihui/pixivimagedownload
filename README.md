# Pixiv 图片筛选器

一个基于 **PySide6** + **Gradio** 的 Pixiv 图片下载与筛选工具，支持关键词搜索、R18/R18G 过滤、AI 模型识别筛选、图片预览与管理。

## 功能特性

- 🔍 **关键词搜索** — 按关键词搜索 Pixiv 作品，支持多页批量获取
- 🖼 **图片预览** — PySide6 桌面 GUI，支持**滚轮缩放** + **鼠标拖拽**浏览大图
- 🚫 **R18 / R18G 过滤** — 可选择屏蔽或仅保留 R18 内容
- 🤖 **AI 模型识别** — 妲厨专用，内置 CNN 卷积神经网络（NahidaCNN），自动识别图片是否为"纳西妲"
- 📥 **批量下载** — 支持多页、多 PID、多页数限制下载，带暂停/停止控制
- 📋 **PID 黑名单** — 手动屏蔽不需要的作品 ID，避免重复出现
- 🔐 **PHPSESSID 自动获取** — 通过 Selenium 自动登录并提取 Cookie
- 🌐 **Web UI 模式** — 基于 Gradio 的轻量网页界面（`app.py`）
- 📦 **一键打包** — 支持 PyInstaller 打包为独立 exe 可执行文件

## 项目结构

```
├── test_app.py              # 主程序 — PySide6 桌面 GUI
├── app.py                   # 备用 — Gradio Web UI
├── build.py                 # 打包脚本 (PyInstaller)
├── Pixiv图片筛选器.spec     # PyInstaller 打包配置
├── pixiv_image_download.py  # 图片下载模块
├── pixiv_imagelink.py       # Pixiv 直链获取模块
├── pixiv_id.py              # 作品 ID 搜索模块
├── get_phpsessid.py         # PHPSESSID 自动获取 (Selenium)
├── instal_webdriver_manager.py  # Edge WebDriver 安装
├── model_script/            # AI 模型模块
│   ├── param.py             # 模型定义 (NahidaCNN) + 数据集
│   ├── train.py             # 模型训练脚本
│   ├── predict.py           # PyTorch 推理
│   └── function.py          # ONNX 转换 & 推理
├── models/                  # 预训练模型文件 (.pth / .onnx)
├── datasets/pic_datasets/   # 训练数据集 (0/1 二分类)
├── requirements.txt         # torch_cpu Python 依赖
├── phpsessid.txt            # Pixiv 登录凭证 (需自行填写)
└── pids_filter.txt          # PID 黑名单
```

## 快速开始

### 1. 环境要求

- Python 3.11+
- 需要自备网络代理工具（访问 Pixiv 所需）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 PHPSESSID

在 `phpsessid.txt` 中写入你的 Pixiv PHPSESSID，或运行自动获取脚本：

```bash
python get_phpsessid.py
```

> 自动获取会打开 Edge 浏览器跳转到 Pixiv 登录页，登录后自动提取 Cookie。

### 4. 运行

**桌面 GUI（推荐）：**

```bash
python test_app.py
```

**Web UI（备用）：**

```bash
python app.py
```

### 5. 打包为 exe

```bash
python build.py
```

或直接使用 PyInstaller：

```bash
pyinstaller Pixiv图片筛选器.spec
```

打包后的文件在 `release/` 目录下。

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

### 设置页面（Tab 3）

- **下载限制**：按"图片张数"或"PID 个数"限制下载量
- **页码限制**：跳过页数过多的作品（如跳过超过 5 页的合辑）
- **模型识别**：启用/关闭 AI 识别功能

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
| gradio | Web UI 框架 |
| requests | Pixiv API 请求 |
| selenium | 自动获取 PHPSESSID |
| onnxruntime | 模型推理（用户端） |
| torch / torchvision | 模型训练（开发端） |
| numpy / pillow | 图像处理 |
| pyinstaller | 打包为 exe |

## 更新日志

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
