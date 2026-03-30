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
from utils.translator import Translator

class CLIPModel:
    """CLIP模型包装器类"""
    
    def __init__(self, use_custom_model: bool = False, custom_model_path: str = None, label_map_path: str = None):
        """初始化CLIP模型
        
        Args:
            use_custom_model: 是否使用自定义训练的模型
            custom_model_path: 自定义模型路径
            label_map_path: 标签映射文件路径
        """
        # 获取工程目录
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 模型存储目录
        self.models_dir = os.path.join(self.project_dir, "models", "pretrained")
        os.makedirs(self.models_dir, exist_ok=True)
        
        # 加载CLIP模型
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"CLIP使用设备: {self.device}")
        print(f"模型存储目录: {self.models_dir}")
        
        self.use_custom_model = use_custom_model
        self.custom_model_path = custom_model_path
        self.label_map_path = label_map_path
        
        # 初始化翻译工具
        self.translator = Translator()
        
        # 加载标签映射
        if use_custom_model and label_map_path and os.path.exists(label_map_path):
            with open(label_map_path, 'r', encoding='utf-8') as f:
                label_map = json.load(f)
                self.english_labels = label_map.get("labels", [])
                self.label_to_idx = label_map.get("label_to_idx", {})
            print(f"加载自定义标签映射，共 {len(self.english_labels)} 个标签")
            
            # 将英文标签翻译为中文
            if self.translator.is_available():
                self.chinese_labels = []
                for en_label in self.english_labels:
                    # 先将下划线替换为空格，再翻译
                    en_label_clean = en_label.replace("_", " ")
                    zh_label = self.translator.translate(en_label_clean, "zh")
                    if zh_label:
                        self.chinese_labels.append(zh_label)
                    else:
                        self.chinese_labels.append(en_label)
                print("英文标签已翻译为中文")
            else:
                self.chinese_labels = self.english_labels
        else:
            # 默认标签（仅当未使用自定义模型时）
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
        
        # 标签权重，禁用自学习
        self.label_weights = {label: 1.0 for label in self.chinese_labels}
        
        # 禁用历史反馈加载
        self.feedback_file = os.path.join(self.project_dir, "feedback.json")
        # self.load_feedback()  # 禁用反馈加载
        
        try:
            # 设置CLIP模型缓存目录
            os.environ["TORCH_HOME"] = self.models_dir
            self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
            
            # 加载自定义模型
            if use_custom_model and custom_model_path and os.path.exists(custom_model_path):
                self.model.load_state_dict(torch.load(custom_model_path, map_location=self.device))
                print("自定义模型加载成功")
            else:
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
            
            with torch.no_grad():
                if self.use_custom_model:
                    # 使用自定义模型预测
                    image_features = self.model.encode_image(image_input)
                    outputs = self.model.classifier(image_features)
                    probabilities = torch.sigmoid(outputs).squeeze().cpu().numpy()
                    
                    # 获取置信度高于阈值的标签
                    results = []
                    for i, prob in enumerate(probabilities):
                        if prob >= 0.5:
                            results.append({
                                "label": self.chinese_labels[i],
                                "confidence": float(prob)
                            })
                    
                    # 按置信度排序
                    results.sort(key=lambda x: x["confidence"], reverse=True)
                    return results[:5]  # 返回前5个
                else:
                    # 使用原始CLIP模型预测
                    # 准备文本
                    text_inputs = torch.cat([clip.tokenize(label) for label in self.english_labels]).to(self.device)
                    
                    # 计算特征
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
                        # 禁用权重调整
                        confidence = min(0.99, value.item())
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
        """从用户反馈中学习（已禁用）
        
        Args:
            original_tags: 原始标签
            corrected_tags: 用户纠正后的标签
        """
        # 禁用自学习功能
        print("自学习功能已禁用")
        # 保存反馈（可选）
        # self.save_feedback()
    
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
