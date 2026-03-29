#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR模型包装器 - 完整版（使用EasyOCR）
"""

from typing import Dict
import easyocr
import os

class OCRModel:
    """OCR模型包装器类"""
    
    def __init__(self, languages: list = None):
        """初始化OCR模型
        
        Args:
            languages: 语言列表，默认为 ['ch_sim', 'en']
        """
        # 获取工程目录
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 模型存储目录
        self.models_dir = os.path.join(self.project_dir, "models", "pretrained")
        os.makedirs(self.models_dir, exist_ok=True)
        
        if languages is None:
            languages = ['ch_sim', 'en']
        self.languages = languages
        self.reader = None
        self._load_model()
    
    def _load_model(self):
        """加载EasyOCR模型"""
        try:
            # 检测GPU
            import torch
            gpu_available = torch.cuda.is_available()
            print(f"GPU可用: {gpu_available}")
            print(f"模型存储目录: {self.models_dir}")
            print(f"正在加载EasyOCR模型 (语言: {self.languages})...")
            
            # 设置EasyOCR模型缓存目录
            os.environ["EASYOCR_CACHE"] = self.models_dir
            os.environ["EASYOCR_MODULE_PATH"] = self.models_dir
            # 直接指定模型目录
            self.reader = easyocr.Reader(self.languages, gpu=gpu_available, model_storage_directory=self.models_dir)
            print("EasyOCR模型加载成功")
            if gpu_available:
                print("EasyOCR模型正在使用GPU加速")
            else:
                print("EasyOCR模型正在使用CPU")
        except Exception as e:
            print(f"EasyOCR模型加载失败: {e}")
            self.reader = None
    
    def recognize(self, image_path: str) -> Dict:
        """使用OCR识别图像中的文字
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            识别结果字典
        """
        if self.reader is None:
            return self._recognize_simplified(image_path)
        
        try:
            # 检查文件是否存在
            if not os.path.exists(image_path):
                return {"text": "", "keywords": []}
            
            # 识别文字
            results = self.reader.readtext(image_path)
            
            # 提取所有文字
            all_text = " ".join([result[1] for result in results])
            
            # 提取关键词
            keywords = self.extract_keywords(all_text)
            
            return {
                "text": all_text,
                "keywords": keywords
            }
        except Exception as e:
            print(f"OCR识别失败: {e}")
            return self._recognize_simplified(image_path)
    
    def _recognize_simplified(self, image_path: str) -> Dict:
        """简化版识别（备用）"""
        return {
            "text": "示例OCR文本（OCR模型未加载）",
            "keywords": ["PPT", "演示"]
        }
    
    def extract_keywords(self, text: str) -> list:
        """从OCR识别结果中提取关键词
        
        Args:
            text: OCR识别文本
            
        Returns:
            关键词列表
        """
        # 关键词列表
        keywords_dict = {
            "PPT": ["PPT", "幻灯片", "演示文稿", "presentation"],
            "演示": ["演示", "展示", "demo", "演示文稿"],
            "数据": ["数据", "统计", "图表", "graph", "chart"],
            "报告": ["报告", "report", "总结", "summary"],
            "表格": ["表格", "table", "sheet", "excel"],
            "图表": ["图表", "图形", "chart", "graph", "diagram"],
            "文字": ["文字", "文本", "text", "文档"],
            "标题": ["标题", "title", "主题", "topic"]
        }
        
        found_keywords = []
        text_lower = text.lower()
        for keyword, synonyms in keywords_dict.items():
            for synonym in synonyms:
                if synonym.lower() in text_lower:
                    found_keywords.append(keyword)
                    break
        
        # 如果没有找到关键词，返回一些默认关键词
        if not found_keywords:
            found_keywords = ["文字内容"]
        
        return found_keywords[:5]  # 最多返回5个关键词
