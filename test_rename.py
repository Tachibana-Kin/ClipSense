#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试重命名功能
"""

import os
import tempfile
from utils.file_renamer import FileRenamer

# 创建临时测试文件
test_content = b"Test file content"

# 创建临时目录
with tempfile.TemporaryDirectory() as temp_dir:
    # 创建测试文件（包含中文字符）
    test_file = os.path.join(temp_dir, "测试视频.mp4")
    with open(test_file, 'wb') as f:
        f.write(test_content)
    
    print(f"创建测试文件: {test_file}")
    
    # 测试重命名功能
    renamer = FileRenamer()
    tags = ["动作", "冒险", "科幻"]
    
    try:
        new_path = renamer.rename_file(test_file, tags)
        print(f"重命名成功: {new_path}")
        print(f"新文件名: {os.path.basename(new_path)}")
        
        # 验证文件是否存在
        if os.path.exists(new_path):
            print("文件重命名后存在")
        else:
            print("文件重命名后不存在")
            
    except Exception as e:
        print(f"重命名失败: {str(e)}")
        import traceback
        traceback.print_exc()
