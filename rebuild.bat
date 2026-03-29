@echo off
cd "%~dp0"
echo 正在重新构建可执行文件...
venv\Scripts\pyinstaller --onefile --windowed --name Video_Manager main.py
echo 构建完成！可执行文件位于 dist\Video_Manager.exe
echo 按任意键退出...
pause >nul
