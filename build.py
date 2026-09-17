"""
Pixiv 图片筛选器 - 打包脚本
使用 PyInstaller 将 main.py 打包为独立可执行文件
"""

import os
import sys
import subprocess
import shutil

# 确保控制台输出 UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python 3.6 及以下没有 reconfigure
        pass

# ==================== 配置 ====================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ENTRY_POINT = "main.py"
APP_NAME = "Pixiv图片筛选器"
ICON_FILE = "pixiv.ico"
DIST_DIR = os.path.join(PROJECT_ROOT, "release")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
SPEC_FILE = os.path.join(PROJECT_ROOT, f"{APP_NAME}.spec")

# 需要打包进去的额外数据文件 (源路径, 目标路径)
# 元组格式: (源文件/目录, 目标目录)
# 默认背景图由 theme/default_image/ 提供（见 config_logic._find_default_image，
# 优先取「1」号预设），已随下面的 theme 一并打包，这里不需要单独的图片文件。
DATA_FILES = [
    ("pixiv.ico", "."),                 # 程序图标
    ("ui/app.qss", "ui"),               # 统一样式表（_load_app_qss 按 ui/app.qss 查找）
    ("theme", "theme"),                 # 预设背景图（resource_path('theme/default_image')）
]

# 注意：不要把 pids_filter.txt 打包进去。
# 它是**用户自己积累的屏蔽列表**（本机 69 个 PID），新用户应当从空列表开始。
# 不打包即可满足：logic/image_logic.py 用 'a+' 打开，缺失时会自动创建空文件。

# 需要额外引入的隐藏模块
HIDDEN_IMPORTS = [
    # selenium 动态加载的子模块（PyInstaller 静态分析检测不到）
    "selenium.webdriver.edge.webdriver",
    "selenium.webdriver.edge.service",
    "selenium.webdriver.edge.options",
    "selenium.webdriver.common.by",
    "selenium.webdriver.support.ui",
    "selenium.webdriver.support.expected_conditions",
    "webdriver_manager.microsoft",
    # model_script 包
    "model_script",
    "model_script.function",
    "onnxruntime",
]

# 需要排除的模块（减小体积）
EXCLUDES = [
    "tkinter",
    "matplotlib",
    "scipy",
    "PIL.ImageShow",  # pillow 部分功能
    "setuptools",
    # 已改用 ONNX Runtime，不再需要 torch
    "torch",
    "torchvision",
]


# ==================== 发布版（--release）====================
# 下面这些必须放在 **exe 同级目录**：代码用 os.path.abspath(".")（启动时的
# 工作目录）去定位它们，塞进 bundle 是没用的。
RELEASE_COPY_TO_EXE_DIR = [
    # (源, 说明, 只复制这些后缀；None = 整个复制)
    # model_dir = abspath(".")/models —— 「模型识别」功能靠它。
    # 必须过滤：models/ 里还有训练用的 *.pth（本机 5 个共 160MB），
    # 被 .gitignore 排除、运行时完全用不到，不筛就会把发布包撑大 4 倍。
    ("models", "模型文件（模型识别需要）", (".onnx", ".onnx.data")),
    # bg_search_dirs 也基于 abspath(".") —— 背景图下拉框靠它
    ("theme", "预设背景图", None),
    # pids_filter.txt 刻意不在清单里：它是用户的个人屏蔽列表，
    # 应由程序首次运行时自动创建为空文件（见上文 DATA_FILES 的说明）。
]

# 程序会按需创建这些目录，预先建好只是让发布包结构一目了然
RELEASE_EMPTY_DIRS = ["config", "saved", "temp"]


def dir_size_mb(path):
    """统计目录总大小（MB）"""
    total = 0
    for root, _dirs, files in os.walk(path):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(root, fn))
            except OSError:
                pass
    return total / 1024 / 1024


def _copy_tree_filtered(src, dst, suffixes):
    """按后缀白名单复制目录；suffixes 为 None 时整个复制。返回复制文件数"""
    if os.path.exists(dst):
        shutil.rmtree(dst)
    if suffixes is None:
        shutil.copytree(src, dst)
        return sum(len(fs) for _r, _d, fs in os.walk(dst))
    count = 0
    for root, _dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target = dst if rel == '.' else os.path.join(dst, rel)
        os.makedirs(target, exist_ok=True)
        for fn in files:
            if not fn.lower().endswith(suffixes):
                continue
            shutil.copy2(os.path.join(root, fn), os.path.join(target, fn))
            count += 1
    return count


def copy_release_runtime(app_dir):
    """把必须位于 exe 同级的运行期数据复制过去"""
    for rel, desc, suffixes in RELEASE_COPY_TO_EXE_DIR:
        src = os.path.join(PROJECT_ROOT, rel)
        if not os.path.exists(src):
            print(f"  ⚠ 跳过（源不存在）: {rel}")
            continue
        dst = os.path.join(app_dir, rel)
        if os.path.isdir(src):
            n = _copy_tree_filtered(src, dst, suffixes)
            tag = f"{n} 个文件" + ("（已过滤）" if suffixes else "")
        else:
            shutil.copy2(src, dst)
            tag = "1 个文件"
        size = dir_size_mb(dst) if os.path.isdir(dst) else os.path.getsize(dst) / 1024 / 1024
        print(f"  ✓ {rel:<18} {size:7.1f} MB  {tag}  {desc}")
    for d in RELEASE_EMPTY_DIRS:
        os.makedirs(os.path.join(app_dir, d), exist_ok=True)
    print(f"  ✓ 预建空目录: {', '.join(RELEASE_EMPTY_DIRS)}")


def write_usage_note(app_dir):
    """在发布目录里生成使用说明"""
    note = f"""【{APP_NAME}】使用说明

启动
    双击 {APP_NAME}.exe 即可，无需安装 Python。

注意
    本文件夹必须整体保留，不要单独移动其中某个文件 ——
    程序依赖同级的 models/、theme/ 等目录。

首次使用
    1. 打开「设置」页填入 PHPSESSID（可点「获取」自动抓取，需要 Edge 浏览器）
    2. 下载的图片保存在 saved/，可用左下角「打开目录」按钮直达

目录说明
    models/   模型文件（「模型识别」功能需要）
    theme/    预设背景图
    saved/    下载的图片
    temp/     预览图缓存（可在设置页清理）
    config/   界面设置与 PHPSESSID
    pids_filter.txt  屏蔽列表（初始为空，勾选各页的「pid屏蔽」后累积）
"""
    with open(os.path.join(app_dir, '使用说明.txt'), 'w', encoding='utf-8') as f:
        f.write(note)
    print("  ✓ 使用说明.txt")


def make_zip(app_dir):
    """打包成 zip 放到 release/ 下"""
    print(f"\n🗜  压缩 {APP_NAME} ...")
    archive = shutil.make_archive(os.path.join(DIST_DIR, APP_NAME), 'zip',
                                  root_dir=DIST_DIR, base_dir=APP_NAME)
    print(f"  ✓ {os.path.basename(archive)}  ({os.path.getsize(archive) / 1024 / 1024:.1f} MB)")


def check_pyinstaller():
    """检查 PyInstaller 是否已安装"""
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
        return True
    except ImportError:
        print("❌ PyInstaller 未安装，正在安装...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            cwd=PROJECT_ROOT
        )
        if result.returncode == 0:
            print("✅ PyInstaller 安装成功")
            return True
        else:
            print("❌ PyInstaller 安装失败，请手动执行: pip install pyinstaller")
            return False


def build(args):
    """执行打包"""
    if not check_pyinstaller():
        return False

    # 清理旧的构建文件
    for path in [DIST_DIR, BUILD_DIR, SPEC_FILE]:
        if os.path.exists(path):
            print(f"清理: {path}")
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    # 构建 PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",                    # 覆盖输出目录
        "--clean",                        # 清理缓存
        "--strip",                        # 去掉调试符号
        "--name", APP_NAME,               # 输出名称
    ]

    # 图标
    icon_path = os.path.join(PROJECT_ROOT, ICON_FILE)
    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
    else:
        print(f"⚠ 图标文件不存在 ({ICON_FILE})，将使用默认图标")

    # 数据文件
    for src_rel, dst in DATA_FILES:
        src_path = os.path.join(PROJECT_ROOT, src_rel)
        if os.path.exists(src_path):
            cmd.extend(["--add-data", f"{src_path}{os.pathsep}{dst}"])
        else:
            print(f"⚠ 数据文件不存在: {src_rel}，将跳过")

    # 隐藏导入
    for mod in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", mod])

    # 排除模块（减小体积）
    for mod in EXCLUDES:
        cmd.extend(["--exclude-module", mod])

    # 输出目录
    cmd.extend(["--distpath", DIST_DIR])

    # 模式选择
    # --onedir: 生成目录（启动快；--release 发布版固定用这个）
    # --onefile: 生成单个 exe（文件大，启动稍慢）
    if args.release and args.onefile:
        print("⚠ --release 与 --onefile 互斥：发布版按 onedir 处理")
    if args.onefile and not args.release:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # 窗口模式（不显示控制台）
    # 开发调试用 console（能看到完整终端输出）；--release 发布版自动隐藏控制台。
    # 隐藏控制台是安全的：实测 windowed 下 sys.stdout/sys.stderr 会是 None，
    # 但 CPython 的 print() 遇到 None 直接静默返回、不抛异常；运行时路径里
    # 也没有任何 sys.stdout.reconfigure() 调用（只有本脚本构建时用）。
    if args.windowed or args.release:
        cmd.append("--windowed")

    # 添加入口文件
    entry_path = os.path.join(PROJECT_ROOT, ENTRY_POINT)
    cmd.append(entry_path)

    print("=" * 60)
    print(f"🔨 开始打包: {APP_NAME}")
    print(f"📂 入口文件: {ENTRY_POINT}")
    print(f"📦 输出目录: {DIST_DIR}")
    print("=" * 60)
    print()
    print("执行命令:")
    print(" ".join(cmd))
    print()

    # 执行打包
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        app_dir = os.path.join(DIST_DIR, APP_NAME)
        print()
        print("=" * 60)
        print(f"✅ 打包成功!")
        print(f"📁 可执行文件位于: {app_dir}")
        if args.release:
            print("=" * 60)
            print()
            print("📦 整理发布目录（把运行期数据放到 exe 同级）...")
            copy_release_runtime(app_dir)
            write_usage_note(app_dir)
            print()
            print(f"📊 成品体积: {dir_size_mb(app_dir):.1f} MB")
            if args.zip:
                make_zip(app_dir)
        print("=" * 60)
        return True
    else:
        print()
        print("❌ 打包失败!")
        return False


def clean():
    """清理构建产物"""
    for path in [DIST_DIR, BUILD_DIR, SPEC_FILE]:
        if os.path.exists(path):
            print(f"清理: {path}")
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    print("✅ 清理完成")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pixiv 图片筛选器 - 打包工具")
    parser.add_argument("--clean", action="store_true", help="清理构建产物")
    parser.add_argument("--onefile", action="store_true", help="打包为单个 exe 文件")
    parser.add_argument("--windowed", action="store_true", help="无控制台窗口模式")
    parser.add_argument("--release", action="store_true",
                        help="发布版：onedir + 隐藏控制台 + models/theme 等放到 exe 同级")
    parser.add_argument("--zip", action="store_true",
                        help="配合 --release，额外打成 zip 便于分发")

    args = parser.parse_args()

    if args.clean:
        clean()
    else:
        build(args)
        print()
        print("💡 提示:")
        print("  - 【发布版】打包可分发软件: python build.py --release")
        print("  - 【发布版】同时打成 zip  : python build.py --release --zip")
        print("  - 开发用（带控制台）      : python build.py")
        print("  - 打包为单个 exe          : python build.py --onefile")
        print("  - 清理构建产物            : python build.py --clean")
