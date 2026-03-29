#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Whisper模型包装器 - 完整版
"""

from typing import Dict
import os

# 获取工程目录
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 模型存储目录
models_dir = os.path.join(project_dir, "models", "pretrained")
os.makedirs(models_dir, exist_ok=True)

# 设置Whisper模型缓存目录
os.environ["WHISPER_CACHE"] = models_dir

import whisper

class WhisperModel:
    """Whisper模型包装器类"""
    
    def __init__(self, model_size: str = "base"):
        """初始化Whisper模型
        
        Args:
            model_size: 模型大小 (tiny, base, small, medium, large)
        """
        self.project_dir = project_dir
        self.models_dir = models_dir
        self.model_size = model_size
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载Whisper模型"""
        try:
            # 检测GPU
            import torch
            gpu_available = torch.cuda.is_available()
            print(f"GPU可用: {gpu_available}")
            print(f"模型存储目录: {self.models_dir}")
            print(f"正在加载Whisper模型 ({self.model_size})...")
            
            # 直接指定模型下载目录
            self.model = whisper.load_model(self.model_size, download_root=self.models_dir)
            print("Whisper模型加载成功")
            if gpu_available:
                print("Whisper模型正在使用GPU加速")
            else:
                print("Whisper模型正在使用CPU")
        except Exception as e:
            print(f"Whisper模型加载失败: {e}")
            self.model = None
    
    def transcribe(self, video_path: str) -> Dict[str, str]:
        """使用Whisper模型转录视频中的音频
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            转录结果字典
        """
        if self.model is None:
            return self._transcribe_simplified(video_path)
        
        try:
            # 检查文件是否存在
            if not os.path.exists(video_path):
                return {"text": "", "segments": []}
            
            # 转录音频
            result = self.model.transcribe(video_path, language="zh")
            
            return {
                "text": result["text"],
                "segments": result.get("segments", [])
            }
        except Exception as e:
            print(f"Whisper转录失败: {e}")
            return self._transcribe_simplified(video_path)
    
    def _transcribe_simplified(self, video_path: str) -> Dict[str, str]:
        """简化版转录（备用）"""
        return {
            "text": "这是一个示例转录文本（Whisper模型未加载）。",
            "segments": []
        }
    
    def extract_keywords(self, text: str) -> list:
        """从转录文本中提取关键词
        
        Args:
            text: 转录文本
            
        Returns:
            关键词列表
        """
        # 关键词列表
        keywords_dict = {
            "会议": ["会议", "讨论", "汇报", "总结", "决策"],
            "预算": ["预算", "成本", "费用", "支出", "收入", "财务"],
            "报告": ["报告", "分析", "数据", "统计", "结果"],
            "演示": ["演示", "展示", "介绍", "说明", "讲解"],
            "培训": ["培训", "学习", "教学", "课程", "教育"],
            "演讲": ["演讲", "发言", "讲话", "致辞", "讲座"],
            "项目": ["项目", "计划", "方案", "实施", "执行"],
            "团队": ["团队", "合作", "协作", "配合", "协调"]
        }
        
        found_keywords = []
        for keyword, synonyms in keywords_dict.items():
            for synonym in synonyms:
                if synonym in text:
                    found_keywords.append(keyword)
                    break
        
        # 如果没有找到关键词，返回一些默认关键词
        if not found_keywords:
            found_keywords = ["语音内容"]
        
        return found_keywords[:5]  # 最多返回5个关键词
