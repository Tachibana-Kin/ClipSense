#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理器模块
"""

import os
import json
from pathlib import Path

class ConfigManager:
    """配置管理器类"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        self.default_config = {
            "thumbnail": {
                "count": 3,  # 每个视频的缩略图数量
                "interval_minutes": 2,  # 截图间隔（分钟）
                "size": [300, 200],  # 缩略图尺寸
                "quality": 75  # JPEG压缩质量
            }
        }
        self.config = self.load_config()
    
    def load_config(self) -> dict:
        """加载配置文件
        
        Returns:
            配置字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self.default_config
        else:
            return self.default_config
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def get_thumbnail_count(self) -> int:
        """获取缩略图数量
        
        Returns:
            缩略图数量
        """
        return self.config.get("thumbnail", {}).get("count", self.default_config["thumbnail"]["count"])
    
    def set_thumbnail_count(self, count: int):
        """设置缩略图数量
        
        Args:
            count: 缩略图数量
        """
        if "thumbnail" not in self.config:
            self.config["thumbnail"] = {}
        self.config["thumbnail"]["count"] = max(1, min(10, count))
        self.save_config()
    
    def get_thumbnail_interval(self) -> int:
        """获取截图间隔（分钟）
        
        Returns:
            截图间隔
        """
        return self.config.get("thumbnail", {}).get("interval_minutes", self.default_config["thumbnail"]["interval_minutes"])
    
    def set_thumbnail_interval(self, interval: int):
        """设置截图间隔（分钟）
        
        Args:
            interval: 截图间隔
        """
        if "thumbnail" not in self.config:
            self.config["thumbnail"] = {}
        self.config["thumbnail"]["interval_minutes"] = max(1, min(10, interval))
        self.save_config()
    
    def get_thumbnail_size(self) -> list:
        """获取缩略图尺寸
        
        Returns:
            缩略图尺寸 [width, height]
        """
        return self.config.get("thumbnail", {}).get("size", self.default_config["thumbnail"]["size"])
    
    def set_thumbnail_size(self, width: int, height: int):
        """设置缩略图尺寸
        
        Args:
            width: 宽度
            height: 高度
        """
        if "thumbnail" not in self.config:
            self.config["thumbnail"] = {}
        self.config["thumbnail"]["size"] = [max(100, min(800, width)), max(100, min(600, height))]
        self.save_config()
    
    def get_thumbnail_quality(self) -> int:
        """获取缩略图压缩质量
        
        Returns:
            压缩质量（0-100）
        """
        return self.config.get("thumbnail", {}).get("quality", self.default_config["thumbnail"]["quality"])
    
    def set_thumbnail_quality(self, quality: int):
        """设置缩略图压缩质量
        
        Args:
            quality: 压缩质量（0-100）
        """
        if "thumbnail" not in self.config:
            self.config["thumbnail"] = {}
        self.config["thumbnail"]["quality"] = max(1, min(100, quality))
        self.save_config()
