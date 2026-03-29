#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频管理工具主脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from video_processor.video_analyzer import VideoAnalyzer
from gui.main_window import MainWindow
from PyQt5.QtWidgets import QApplication

def main():
    """主函数"""
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()