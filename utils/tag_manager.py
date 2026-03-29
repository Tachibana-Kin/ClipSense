#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
标签管理模块
"""

from typing import List, Dict, Set

class TagManager:
    """标签管理类"""
    
    def __init__(self):
        """初始化标签管理器"""
        self.tags = []
    
    def merge_tags(self, clip_tags: List[Dict[str, float]], whisper_keywords: List[str], ocr_keywords: List[str], clothes_tags: List[Dict[str, float]]) -> List[str]:
        """融合来自不同来源的标签
        
        Args:
            clip_tags: CLIP模型生成的标签
            whisper_keywords: Whisper模型提取的关键词
            ocr_keywords: OCR模型提取的关键词
            clothes_tags: 服饰识别模型生成的标签
            
        Returns:
            融合后的标签列表
        """
        # 收集所有标签
        all_tags = set()
        
        # 添加CLIP标签
        for tag_info in clip_tags:
            all_tags.add(tag_info["label"])
        
        # 添加Whisper关键词
        all_tags.update(whisper_keywords)
        
        # 添加OCR关键词
        all_tags.update(ocr_keywords)
        
        # 添加服饰标签
        for tag_info in clothes_tags:
            all_tags.add(tag_info["label"])
        
        # 转换为列表并存储
        self.tags = list(all_tags)
        return self.tags
    
    def add_tag(self, tag: str) -> bool:
        """添加标签
        
        Args:
            tag: 要添加的标签
            
        Returns:
            是否添加成功
        """
        if tag not in self.tags:
            self.tags.append(tag)
            return True
        return False
    
    def remove_tag(self, tag: str) -> bool:
        """删除标签
        
        Args:
            tag: 要删除的标签
            
        Returns:
            是否删除成功
        """
        if tag in self.tags:
            self.tags.remove(tag)
            return True
        return False
    
    def update_tag(self, old_tag: str, new_tag: str) -> bool:
        """更新标签
        
        Args:
            old_tag: 旧标签
            new_tag: 新标签
            
        Returns:
            是否更新成功
        """
        if old_tag in self.tags:
            index = self.tags.index(old_tag)
            self.tags[index] = new_tag
            return True
        return False
    
    def get_tags(self) -> List[str]:
        """获取所有标签
        
        Returns:
            标签列表
        """
        return self.tags
    
    def clear_tags(self):
        """清空所有标签"""
        self.tags = []