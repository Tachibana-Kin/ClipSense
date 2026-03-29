#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLIP模型包装器 - 带自学习能力（完整版）
"""

from PIL import Image
from typing import List, Dict
import json
import os
import torch
import clip

class CLIPModel:
    """CLIP模型包装器类"""
    
    def __init__(self):
        """初始化CLIP模型"""
        # 中文标签映射
        self.chinese_labels = [
            "会议", "PPT", "西装", "夜晚", "街道", "无人", "预算", "红色裙子",
            "办公室", "户外", "室内", "演讲", "演示", "讨论", "团队", "个人",
            "白天", "晚上", "早晨", "下午", "城市", "乡村", "自然", "建筑",
            "交通工具", "动物", "植物", "食物", "饮料", "电子设备", "文档",
            "图表", "数据", "地图", "照片", "视频", "音乐", "运动", "休息"
        ]
        
        # 英文标签（用于CLIP）
        self.english_labels = [
            "meeting", "PPT presentation", "suit", "night", "street", "no person", "budget", "red dress",
            "office", "outdoor", "indoor", "speech", "presentation", "discussion", "team", "individual",
            "daytime", "evening", "morning", "afternoon", "city", "countryside", "nature", "building",
            "vehicle", "animal", "plant", "food", "drink", "electronic device", "document",
            "chart", "data", "map", "photo", "video", "music", "sports", "rest"
        ]
        
        # 标签权重，用于自学习
        self.label_weights = {label: 1.0 for label in self.chinese_labels}
        
        # 获取工程目录
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 模型存储目录
        self.models_dir = os.path.join(self.project_dir, "models", "pretrained")
        os.makedirs(self.models_dir, exist_ok=True)
        
        # 加载历史反馈
        self.feedback_file = os.path.join(self.project_dir, "feedback.json")
        self.load_feedback()
        
        # 加载CLIP模型
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"CLIP使用设备: {self.device}")
        print(f"模型存储目录: {self.models_dir}")
        try:
            # 设置CLIP模型缓存目录
            os.environ["TORCH_HOME"] = self.models_dir
            self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
            print("CLIP模型加载成功")
        except Exception as e:
            print(f"CLIP模型加载失败: {e}，将使用简化版")
            self.model = None
            self.preprocess = None
    
    def predict(self, image_path: str) -> List[Dict[str, float]]:
        """使用CLIP模型预测图像标签
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            标签及其置信度列表
        """
        if self.model is None:
            return self._predict_simplified(image_path)
        
        try:
            # 加载图像
            image = Image.open(image_path).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # 准备文本
            text_inputs = torch.cat([clip.tokenize(label) for label in self.english_labels]).to(self.device)
            
            # 计算特征
            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                text_features = self.model.encode_text(text_inputs)
                
                # 归一化特征
                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features /= text_features.norm(dim=-1, keepdim=True)
                
                # 计算相似度
                similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
                
                # 获取前5个最可能的标签
                values, indices = similarity[0].topk(5)
                
                results = []
                for value, index in zip(values, indices):
                    chinese_label = self.chinese_labels[index]
                    # 应用权重调整
                    weight_factor = self.label_weights.get(chinese_label, 1.0)
                    confidence = min(0.99, value.item() * weight_factor)
                    results.append({
                        "label": chinese_label,
                        "confidence": confidence
                    })
                
                return results
        except Exception as e:
            print(f"CLIP预测失败: {e}")
            return self._predict_simplified(image_path)
    
    def _predict_simplified(self, image_path: str) -> List[Dict[str, float]]:
        """简化版预测（备用）"""
        import random
        results = []
        
        # 根据权重选择标签
        weights = [self.label_weights.get(label, 1.0) for label in self.chinese_labels]
        selected_labels = random.choices(
            self.chinese_labels, 
            weights=weights, 
            k=min(5, len(self.chinese_labels))
        )
        
        # 去重
        selected_labels = list(set(selected_labels))
        
        for label in selected_labels:
            base_confidence = random.uniform(0.3, 0.7)
            weight_factor = self.label_weights.get(label, 1.0)
            confidence = min(0.95, base_confidence * weight_factor)
            results.append({
                "label": label,
                "confidence": confidence
            })
        
        # 按置信度排序
        results.sort(key=lambda x: x["confidence"], reverse=True)
        
        return results
    
    def learn_from_feedback(self, original_tags: List[str], corrected_tags: List[str]):
        """从用户反馈中学习
        
        Args:
            original_tags: 原始标签
            corrected_tags: 用户纠正后的标签
        """
        # 降低未被选中的原始标签的权重
        for tag in original_tags:
            if tag not in corrected_tags and tag in self.label_weights:
                self.label_weights[tag] = max(0.5, self.label_weights[tag] * 0.9)
        
        # 增加用户添加的标签的权重
        for tag in corrected_tags:
            if tag not in original_tags:
                if tag not in self.label_weights:
                    self.label_weights[tag] = 1.0
                self.label_weights[tag] = min(2.0, self.label_weights[tag] * 1.1)
        
        # 保存反馈
        self.save_feedback()
    
    def load_feedback(self):
        """加载历史反馈"""
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "label_weights" in data:
                        self.label_weights.update(data["label_weights"])
            except Exception:
                pass
    
    def save_feedback(self):
        """保存反馈"""
        data = {
            "label_weights": self.label_weights
        }
        try:
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
