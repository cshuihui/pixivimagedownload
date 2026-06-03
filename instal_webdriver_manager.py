from webdriver_manager.microsoft import EdgeChromiumDriverManager
import os
import shutil
import sys
from selenium.webdriver.edge.service import Service


def get_cache_dir():
    """获取持久化缓存目录（优先 exe 所在目录，回退到用户缓存目录）"""
    # 打包后：exe 所在目录（可写、持久）
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        # 开发环境：项目根目录
        base = os.path.dirname(os.path.abspath(__file__))
    return base


cache_dir = get_cache_dir()


def install_edge_webdriver():
    driver_path = os.path.join(cache_dir, "msedgedriver.exe")
    if os.path.exists(driver_path):
        return Service(driver_path)

    driver_dir = EdgeChromiumDriverManager().install()
    local_path = os.path.join(cache_dir, "msedgedriver.exe")

    if not os.path.exists(local_path):
        shutil.copy(driver_dir, local_path)
        print(f"驱动已复制到: {local_path}")

    return Service(local_path)

if __name__ == "__main__":
    print(cache_dir)