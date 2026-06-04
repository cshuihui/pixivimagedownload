"""
Pixiv 图片筛选器 - 打包脚本
使用 PyInstaller 将 test_app.py 打包为独立可执行文件
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
ENTRY_POINT = "test_app.py"
APP_NAME = "Pixiv图片筛选器"
ICON_FILE = "pixiv.ico"
DIST_DIR = os.path.join(PROJECT_ROOT, "release")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
SPEC_FILE = os.path.join(PROJECT_ROOT, f"{APP_NAME}.spec")

# 需要打包进去的额外数据文件 (源路径, 目标路径)
# 元组格式: (源文件/目录, 目标目录)
DATA_FILES = [
    ("143035291_p0.jpg", "."),          # 默认显示图片
    ("pixiv.ico", "."),                 # 程序图标
    ("model", "model"),                 # 模型文件夹（.pth 文件）
]

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
    # model 包
    "model",
    "model.predict",
    "model.param",
]

# 需要排除的模块（减小体积）
EXCLUDES = [
    "tkinter",
    "matplotlib",
    "scipy",
    "PIL.ImageShow",  # pillow 部分功能
    "setuptools",
    # torch GPU 相关（只用 CPU 推理）
    "torch.cuda",
    "torch.backends.cudnn",
    "torch.distributed",
    "torch.jit",
    "torch.autograd",
    "torch.optim",
]


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
    # --onedir: 生成目录（启动快，便于调试）
    # --onefile: 生成单个 exe（文件大，启动稍慢）
    # 默认使用 onedir 模式
    # cmd.append("--onedir")
    # 如果希望单个 exe 文件，取消下面这行注释，注释掉上面那行
    # cmd.append("--onefile")
    if args.onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # 窗口模式（不显示控制台）
    # 由于有 print 输出和交互，使用 console 模式更方便调试
    # 正式发布可以改为 --windowed
    # cmd.append("--windowed")
    if args.windowed:
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
        print()
        print("=" * 60)
        print(f"✅ 打包成功!")
        print(f"📁 可执行文件位于: {os.path.join(DIST_DIR, APP_NAME)}")
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

    args = parser.parse_args()

    if args.clean:
        clean()
    else:
        build(args)
        print()
        print("💡 提示:")
        print("  - 打包为目录: python build.py")
        print("  - 打包为单个 exe: python build.py --onefile")
        print("  - 无控制台窗口: python build.py --windowed")
        print("  - 清理产物: python build.py --clean")
