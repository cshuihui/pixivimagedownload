import time

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

# 需要先安装 msedgedriver
driver = webdriver.Edge()
driver.get("https://accounts.pixiv.net/login")

# 等待登录完成
WebDriverWait(driver, timeout=240).until(
    lambda d: "accounts.pixiv.net/login" not in d.current_url
)
print("检测到登录成功，正在获取Cookie...")
time.sleep(2)  # 等待Cookie写入完成

cookies = driver.get_cookies()
print(cookies)
driver.quit()

PHPSESSID = [c['value'] for c in cookies if c['domain'] == '.pixiv.net' and c['name'] == 'PHPSESSID']
# 这是生成器表达式，不加next()的话得到的是一个对象，不是值
print(PHPSESSID)