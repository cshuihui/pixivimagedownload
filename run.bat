@echo off
chcp 65001
cd /d "%~dp0"

call .venv\Scripts\activate
REM 激活虚拟环境时 必须加 call，否则运行的是 另一个批处理文件（activate.bat)
REM 导致后面的 python 命令不执行
python pixiv_image_download.py

pause