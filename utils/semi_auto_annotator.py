#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
半自动标注工具
"""

import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
from models.clip_model import CLIPModel
from utils.translator import Translator

class SemiAutoAnnotator:
    """半自动标注器类"""
    
    def __init__(self, dataset_dir: str, output_dir: str):
        """初始化半自动标注器
        
        Args:
            dataset_dir: 数据集目录路径
            output_dir: 标注结果输出目录
        """
        self.dataset_dir = dataset_dir
        self.output_dir = output_dir
        self.clip_model = CLIPModel()
        self.translator = Translator()
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 标注结果文件
        self.annotation_file = os.path.join(output_dir, "annotations.json")
    
    def auto_annotate(self, image_dir: str, confidence_threshold: float = 0.5) -> Dict[str, List[str]]:
        """自动标注图像
        
        Args:
            image_dir: 图像目录路径
            confidence_threshold: 置信度阈值
            
        Returns:
            标注结果字典，键为图像路径，值为标签列表
        """
        print(f"正在自动标注图像目录: {image_dir}")
        
        # 获取所有图像文件
        image_extensions = [".jpg", ".jpeg", ".png", ".bmp"]
        image_files = []
        
        for root, _, files in os.walk(image_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    image_files.append(os.path.join(root, file))
        
        print(f"找到 {len(image_files)} 个图像文件")
        
        # 自动标注每个图像
        annotations = {}
        for image_path in image_files:
            try:
                # 使用CLIP模型预测标签
                predictions = self.clip_model.predict(image_path)
                
                # 过滤置信度高于阈值的标签
                labels = [pred["label"] for pred in predictions if pred["confidence"] >= confidence_threshold]
                
                # 将中文标签翻译为英文
                if self.translator.is_available():
                    translated_labels = self.translator.translate_tags(labels)
                    print(f"标签翻译: {labels} -> {translated_labels}")
                    labels = translated_labels
                
                # 保存标注结果
                relative_path = os.path.relpath(image_path, self.dataset_dir)
                annotations[relative_path] = labels
                
                print(f"标注图像 {relative_path}: {labels}")
            except Exception as e:
                print(f"标注图像 {image_path} 失败: {e}")
        
        print(f"自动标注完成，处理 {len(annotations)} 个图像")
        return annotations
    
    def save_annotations(self, annotations: Dict[str, List[str]]):
        """保存标注结果
        
        Args:
            annotations: 标注结果字典
        """
        with open(self.annotation_file, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, ensure_ascii=False, indent=2)
        print(f"标注结果保存到: {self.annotation_file}")
    
    def load_annotations(self) -> Dict[str, List[str]]:
        """加载标注结果
        
        Returns:
            标注结果字典
        """
        if os.path.exists(self.annotation_file):
            with open(self.annotation_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def open_labelimg(self, image_dir: str):
        """打开LabelImg标注工具
        
        Args:
            image_dir: 图像目录路径
        """
        try:
            import subprocess
            import os
            
            # 确保图像目录存在
            if not os.path.exists(image_dir):
                print(f"图像目录不存在: {image_dir}")
                return
            
            # 创建类别文件
            classes_file = os.path.join(self.output_dir, "classes.txt")
            
            # 加载标注结果，提取所有标签
            annotations = self.load_annotations()
            all_labels = set()
            
            if "train" in annotations:
                for label_list in annotations["train"].values():
                    all_labels.update(label_list)
            
            # 保存类别文件
            with open(classes_file, 'w', encoding='utf-8') as f:
                for label in sorted(all_labels):
                    f.write(label + '\n')
            
            print(f"创建类别文件: {classes_file}")
            print(f"包含 {len(all_labels)} 个类别")
            
            print(f"正在打开LabelImg标注工具")
            print(f"请在LabelImg中执行以下操作:")
            print(f"1. 点击 'File' -> 'Change default saved annotation folder'")
            print(f"2. 选择标注保存目录: {self.output_dir}")
            print(f"3. 点击 'File' -> 'Open Dir'")
            print(f"4. 选择图像目录: {image_dir}")
            print(f"5. 点击 'File' -> 'Change Class List'")
            print(f"6. 选择类别文件: {classes_file}")
            print(f"7. 开始标注")
            
            # 使用虚拟环境中的labelImg.exe可执行文件
            labelimg_exe = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "Scripts", "labelImg.exe")
            if os.path.exists(labelimg_exe):
                # 传递图像目录和类别文件给LabelImg
                subprocess.Popen([labelimg_exe, image_dir, classes_file])
                print("LabelImg已打开，请按照上述步骤进行操作")
            else:
                # 尝试使用labelImg命令
                subprocess.Popen(["labelImg", image_dir, classes_file])
                print("LabelImg已打开，请按照上述步骤进行操作")
        except Exception as e:
            print(f"打开LabelImg失败: {e}")
            print("请确保LabelImg已安装，或使用其他标注工具")
            print(f"您可以手动编辑标注文件: {self.annotation_file}")
            print("\n手动启动LabelImg的方法:")
            print("1. 激活虚拟环境: venv\Scripts\activate")
            print("2. 运行命令: labelImg <image_dir> <classes_file>")
            print("3. 按照上述步骤进行操作")
    
    def update_annotation(self, image_path: str, labels: List[str]):
        """更新标注
        
        Args:
            image_path: 图像路径
            labels: 标签列表
        """
        # 将中文标签翻译为英文
        if self.translator.is_available():
            translated_labels = self.translator.translate_tags(labels)
            print(f"标签翻译: {labels} -> {translated_labels}")
            labels = translated_labels
        
        annotations = self.load_annotations()
        
        # 确定图像属于哪个分割（train/val/test）
        for split in ["train", "val", "test"]:
            if split in annotations:
                for img_path in annotations[split]:
                    full_path = os.path.join(self.dataset_dir, img_path)
                    if full_path == image_path:
                        annotations[split][img_path] = labels
                        self.save_annotations(annotations)
                        print(f"更新标注: {img_path} -> {labels}")
                        return
        
        # 如果图像不在现有标注中，添加到训练集
        relative_path = os.path.relpath(image_path, self.dataset_dir)
        if "train" not in annotations:
            annotations["train"] = {}
        annotations["train"][relative_path] = labels
        self.save_annotations(annotations)
        print(f"创建新标注: {relative_path} -> {labels}")
    
    def create_annotation_file(self, image_dir: str, output_file: str):
        """创建标注文件
        
        Args:
            image_dir: 图像目录路径
            output_file: 输出标注文件路径
        """
        annotations = self.auto_annotate(image_dir)
        
        # 保存为JSON格式
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, ensure_ascii=False, indent=2)
        
        print(f"标注文件创建完成: {output_file}")
    
    def process_dataset(self, confidence_threshold: float = 0.5):
        """处理整个数据集
        
        Args:
            confidence_threshold: 置信度阈值
        """
        # 只处理训练集，验证集和测试集不需要标注
        train_dir = os.path.join(self.dataset_dir, "train")
        if os.path.exists(train_dir):
            print("处理训练集...")
            train_annotations = self.auto_annotate(train_dir, confidence_threshold)
        else:
            train_annotations = {}
        
        # 保存标注结果（只包含训练集）
        all_annotations = {
            "train": train_annotations
        }
        
        # 保存标注结果
        self.save_annotations(all_annotations)
        
        # 打开LabelImg进行手动修正
        self.open_labelimg(train_dir)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="半自动标注工具")
    parser.add_argument("--dataset_dir", type=str, required=True, help="数据集目录路径")
    parser.add_argument("--output_dir", type=str, default="annotations", help="标注结果输出目录")
    parser.add_argument("--confidence_threshold", type=float, default=0.5, help="置信度阈值")
    
    args = parser.parse_args()
    
    # 创建半自动标注器
    annotator = SemiAutoAnnotator(args.dataset_dir, args.output_dir)
    
    # 处理数据集
    annotator.process_dataset(args.confidence_threshold)
    
    print("半自动标注完成！")

if __name__ == "__main__":
    main()
