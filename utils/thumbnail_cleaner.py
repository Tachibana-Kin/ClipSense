#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缩略图清理工具模块
"""

import os
from pathlib import Path
from database.db_manager import DBManager

class ThumbnailCleaner:
    """缩略图清理工具类"""
    
    def __init__(self):
        """初始化缩略图清理工具"""
        self.db_manager = DBManager()
    
    def get_thumbnails_directory(self) -> str:
        """获取缩略图目录路径
        
        Returns:
            缩略图目录路径
        """
        # 使用工程目录下的thumbnails文件夹
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_dir, "thumbnails")
    
    def clean_unused_thumbnails(self) -> int:
        """清理未使用的缩略图
        
        Returns:
            删除的文件数量
        """
        thumbnails_dir = self.get_thumbnails_directory()
        
        # 检查缩略图目录是否存在
        if not os.path.exists(thumbnails_dir):
            return 0
        
        # 获取数据库中所有已使用的缩略图路径
        used_thumbnails = self.db_manager.get_all_thumbnail_paths()
        # 转换为绝对路径并去重
        used_thumbnails_set = set(os.path.abspath(path) for path in used_thumbnails)
        
        # 扫描缩略图目录中的所有文件
        deleted_count = 0
        for file_name in os.listdir(thumbnails_dir):
            file_path = os.path.abspath(os.path.join(thumbnails_dir, file_name))
            
            # 检查文件是否为缩略图且不在已使用列表中
            if os.path.isfile(file_path) and file_path not in used_thumbnails_set:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"删除未使用的缩略图: {file_path}")
                except Exception as e:
                    print(f"删除文件失败 {file_path}: {str(e)}")
        
        return deleted_count
    
    def clean_all_thumbnails(self) -> int:
        """清理所有缩略图
        
        Returns:
            删除的文件数量
        """
        thumbnails_dir = self.get_thumbnails_directory()
        
        # 检查缩略图目录是否存在
        if not os.path.exists(thumbnails_dir):
            return 0
        
        # 扫描缩略图目录中的所有文件
        deleted_count = 0
        for file_name in os.listdir(thumbnails_dir):
            file_path = os.path.join(thumbnails_dir, file_name)
            
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"删除缩略图: {file_path}")
                except Exception as e:
                    print(f"删除文件失败 {file_path}: {str(e)}")
        
        return deleted_count
    
    def get_thumbnails_count(self) -> int:
        """获取当前缩略图数量
        
        Returns:
            缩略图文件数量
        """
        thumbnails_dir = self.get_thumbnails_directory()
        
        # 检查缩略图目录是否存在
        if not os.path.exists(thumbnails_dir):
            return 0
        
        # 统计文件数量
        count = 0
        for file_name in os.listdir(thumbnails_dir):
            file_path = os.path.join(thumbnails_dir, file_name)
            if os.path.isfile(file_path):
                count += 1
        
        return count
