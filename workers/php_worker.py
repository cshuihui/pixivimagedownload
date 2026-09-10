# -*- coding: utf-8 -*-
"""
workers/php_worker.py — PHPSESSID 相关后台任务

从原 test_app.py 拆出：
- check_pixiv（PHP 连通性检测）
- GetPHPSESSIDWorker（通过浏览器自动获取）
- CheckPHPSESSIDWorker（异步检测）

⚠️ 第一阶段仅做代码拆分，逻辑与原 test_app.py 保持一致。
"""

import requests

from PySide6.QtCore import QObject, Signal, Slot

import get_phpsessid as gps


def check_pixiv(php_id):
    """检测 PHPSESSID 是否可用"""
    try:
        response = requests.get(
            "https://www.pixiv.net/ajax/user/extra",
            cookies={"PHPSESSID": php_id},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if response.status_code == 200:
            # 200 不代表一定有效：登录失效时 Pixiv 也可能返回 200 + error=true
            try:
                data = response.json()
                if data.get('error'):
                    msg = data.get('message') or '未知错误'
                    return False, f"❌ PHPSESSID 无效或已过期（error: {msg}），请重新获取"
            except Exception:
                pass  # 非 JSON 响应按成功处理，交由真实请求判定
            return True, "✅ 连接成功"
        else:
            return False, f"❌ 连接失败，状态码: {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "❌ 连接超时"
    except Exception as e:
        return False, f"❌ 连接失败: {e}"


class GetPHPSESSIDWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    @Slot()
    def run(self):
        try:
            php = gps.get_phpsessid()
            self.finished.emit(php)
        except Exception as e:
            self.error.emit(str(e))


class CheckPHPSESSIDWorker(QObject):
    finished = Signal(bool, str)  # (success, message)

    def __init__(self, php):
        super().__init__()
        self.php = php

    @Slot()
    def run(self):
        try:
            success, msg = check_pixiv(self.php)
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, f"检测异常: {e}")
