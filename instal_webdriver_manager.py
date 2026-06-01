from webdriver_manager.microsoft import EdgeChromiumDriverManager
import os
import shutil
from selenium.webdriver.edge.service import Service


file_dir = os.path.dirname(__file__)


def install_edge_webdriver():
    if "msedgedriver.exe" in os.listdir(file_dir):
        return Service(os.path.join(file_dir, "msedgedriver.exe"))
    driver_dir = EdgeChromiumDriverManager().install()
    local_path = os.path.join(file_dir, "msedgedriver.exe")

    if not os.path.exists(local_path):
        shutil.copy(driver_dir, local_path)
        print(f"驱动已复制到: {local_path}")

    return Service(local_path)

if __name__ == "__main__":
    print(os.path.dirname(__file__))