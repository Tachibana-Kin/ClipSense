#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件重命名工具模块
"""

import os
import re
from pathlib import Path
from typing import List

class FileRenamer:
    """文件重命名工具类"""
    
    def __init__(self):
        """初始化文件重命名工具"""
        pass
    
    def sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除无效字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 移除路径组件，防止路径遍历
        filename = os.path.basename(filename)
        
        # 移除无效字符
        invalid_chars = '\\/:*?"<>|'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 移除多余的下划线
        filename = re.sub(r'_+', '_', filename)
        
        # 移除首尾的下划线
        filename = filename.strip('_')
        
        return filename
    
    def generate_filename(self, original_name: str, tags: List[str], max_length: int = 100) -> str:
        """根据标签生成新的文件名
        
        Args:
            original_name: 原始文件名
            tags: 标签列表
            max_length: 文件名最大长度
            
        Returns:
            新的文件名（不含扩展名）
        """
        # 获取原始文件名（不含扩展名）
        original_base = Path(original_name).stem
        
        # 生成标签部分
        if tags:
            # 取前5个标签
            tag_part = '_'.join(tags[:5])
            # 组合文件名
            new_base = f"{original_base}_{tag_part}"
        else:
            new_base = original_base
        
        # 清理文件名
        new_base = self.sanitize_filename(new_base)
        
        # 截断过长的文件名
        if len(new_base) > max_length:
            new_base = new_base[:max_length]
        
        return new_base
    
    def rename_file(self, file_path: str, tags: List[str]) -> str:
        """重命名文件
        
        Args:
            file_path: 文件路径
            tags: 标签列表
            
        Returns:
            新的文件路径
        """
        # 获取文件信息
        file_path = Path(file_path)
        directory = file_path.parent
        original_name = file_path.name
        extension = file_path.suffix
        
        # 生成新的文件名
        new_base = self.generate_filename(original_name, tags)
        new_filename = f"{new_base}{extension}"
        new_path = directory / new_filename
        
        # 避免文件名冲突
        counter = 1
        while new_path.exists():
            new_filename = f"{new_base}_{counter}{extension}"
            new_path = directory / new_filename
            counter += 1
        
        # 重命名文件
        file_path.rename(new_path)
        
        return str(new_path)