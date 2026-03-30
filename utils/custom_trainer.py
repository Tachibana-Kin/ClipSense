#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
模型训练工具
"""

import os
import json
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from models.clip_model import CLIPModel
import clip
from typing import List, Dict

def collate_fn(batch):
    """自定义collate函数，处理变长标签列表
    
    Args:
        batch: 批次数据列表，每个元素是 (image, labels) 元组
        
    Returns:
        images: 图像张量
        labels: 标签列表的列表
    """
    images = torch.stack([item[0] for item in batch])
    labels = [item[1] for item in batch]
    return images, labels


class CustomDataset(Dataset):
    """自定义数据集类"""
    
    def __init__(self, dataset_dir: str, annotations: Dict[str, List[str]], transform=None):
        """初始化数据集
        
        Args:
            dataset_dir: 数据集目录路径
            annotations: 标注结果字典
            transform: 图像变换
        """
        self.dataset_dir = dataset_dir
        self.annotations = annotations
        self.transform = transform
        
        # 构建图像路径和标签列表
        self.image_paths = []
        self.labels = []
        
        for image_path, label_list in annotations.items():
            full_path = os.path.join(dataset_dir, image_path)
            if os.path.exists(full_path):
                self.image_paths.append(full_path)
                self.labels.append(label_list)
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        image_path = self.image_paths[idx]
        labels = self.labels[idx]
        
        # 加载图像
        image = Image.open(image_path).convert("RGB")
        
        # 应用变换
        if self.transform:
            image = self.transform(image)
        
        return image, labels

class CustomTrainer:
    """模型训练器类"""
    
    def __init__(self, dataset_dir: str, annotations_file: str, output_dir: str):
        """初始化模型训练器
        
        Args:
            dataset_dir: 数据集目录路径
            annotations_file: 标注结果文件路径
            output_dir: 模型输出目录
        """
        self.dataset_dir = dataset_dir
        self.annotations_file = annotations_file
        self.output_dir = output_dir
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 加载标注结果
        with open(annotations_file, 'r', encoding='utf-8') as f:
            self.annotations = json.load(f)
        
        # 提取所有标签
        self.all_labels = self._extract_all_labels()
        self.label_to_idx = {label: i for i, label in enumerate(self.all_labels)}
        self.num_classes = len(self.all_labels)
        
        print(f"发现 {self.num_classes} 个标签: {self.all_labels}")
    
    def _extract_all_labels(self) -> List[str]:
        """提取所有标签
        
        Returns:
            标签列表
        """
        labels = set()
        
        # 从训练集、验证集和测试集中提取标签
        for split in ["train", "val", "test"]:
            if split in self.annotations:
                for label_list in self.annotations[split].values():
                    labels.update(label_list)
        
        return sorted(list(labels))
    
    def _create_dataloaders(self, batch_size: int = 32):
        """创建数据加载器
        
        Args:
            batch_size: 批处理大小
            
        Returns:
            训练、验证、测试数据加载器
        """
        # 图像变换
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # 创建数据集
        train_dataset = CustomDataset(
            self.dataset_dir, 
            self.annotations.get("train", {}), 
            transform=transform
        )
        
        val_dataset = CustomDataset(
            self.dataset_dir, 
            self.annotations.get("val", {}), 
            transform=transform
        )
        
        test_dataset = CustomDataset(
            self.dataset_dir, 
            self.annotations.get("test", {}), 
            transform=transform
        )
        
        # 创建数据加载器，使用自定义collate函数处理变长标签列表
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, collate_fn=collate_fn)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, collate_fn=collate_fn)
        
        print(f"训练集: {len(train_dataset)} 样本")
        print(f"验证集: {len(val_dataset)} 样本")
        print(f"测试集: {len(test_dataset)} 样本")
        
        return train_loader, val_loader, test_loader
    
    def _create_model(self):
        """创建模型
        
        Returns:
            模型
        """
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 加载预训练的CLIP模型，使用float32精度
        model, preprocess = clip.load("ViT-B/32", device=device, jit=False)
        model = model.float()  # 转换为float32
        
        # 冻结模型参数
        for param in model.parameters():
            param.requires_grad = False
        
        # 替换分类头
        model.classifier = nn.Linear(model.visual.output_dim, self.num_classes)
        
        return model.to(device)
    
    def _labels_to_one_hot(self, labels_list: List[List[str]]) -> torch.Tensor:
        """将标签列表转换为独热编码
        
        Args:
            labels_list: 标签列表
            
        Returns:
            独热编码张量
        """
        batch_size = len(labels_list)
        one_hot = torch.zeros(batch_size, self.num_classes)
        
        for i, labels in enumerate(labels_list):
            for label in labels:
                if label in self.label_to_idx:
                    one_hot[i, self.label_to_idx[label]] = 1
        
        return one_hot
    
    def train(self, epochs: int = 50, batch_size: int = 32, lr: float = 1e-4):
        """训练模型
        
        Args:
            epochs: 训练轮数
            batch_size: 批处理大小
            lr: 学习率
        """
        # 创建数据加载器
        train_loader, val_loader, test_loader = self._create_dataloaders(batch_size)
        
        # 创建模型
        model = self._create_model()
        device = next(model.parameters()).device
        
        # 定义损失函数和优化器
        criterion = nn.BCEWithLogitsLoss()
        optimizer = optim.Adam(model.classifier.parameters(), lr=lr)
        
        # 训练循环
        best_val_loss = float('inf')
        
        for epoch in range(epochs):
            # 训练阶段
            model.train()
            train_loss = 0.0
            
            for images, labels in train_loader:
                images = images.to(device)
                labels = self._labels_to_one_hot(labels).to(device)
                
                # 前向传播
                with torch.no_grad():
                    image_features = model.encode_image(images)
                outputs = model.classifier(image_features)
                
                # 计算损失
                loss = criterion(outputs, labels)
                
                # 反向传播
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            # 验证阶段
            model.eval()
            val_loss = 0.0
            
            with torch.no_grad():
                for images, labels in val_loader:
                    images = images.to(device)
                    labels = self._labels_to_one_hot(labels).to(device)
                    
                    image_features = model.encode_image(images)
                    outputs = model.classifier(image_features)
                    loss = criterion(outputs, labels)
                    val_loss += loss.item()
            
            # 计算平均损失
            train_loss /= len(train_loader)
            val_loss /= len(val_loader)
            
            print(f"Epoch {epoch+1}/{epochs}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
            
            # 保存最佳模型
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                model_path = os.path.join(self.output_dir, "best_model.pth")
                torch.save(model.state_dict(), model_path)
                print(f"保存最佳模型到: {model_path}")
        
        # 保存标签映射
        label_map_path = os.path.join(self.output_dir, "label_map.json")
        with open(label_map_path, 'w', encoding='utf-8') as f:
            json.dump({
                "labels": self.all_labels,
                "label_to_idx": self.label_to_idx
            }, f, ensure_ascii=False, indent=2)
        print(f"保存标签映射到: {label_map_path}")
        
        # 测试模型
        self.test(model, test_loader)
    
    def test(self, model, test_loader):
        """测试模型
        
        Args:
            model: 模型
            test_loader: 测试数据加载器
        """
        device = next(model.parameters()).device
        model.eval()
        
        test_loss = 0.0
        criterion = nn.BCEWithLogitsLoss()
        
        with torch.no_grad():
            for images, labels in test_loader:
                images = images.to(device)
                labels = self._labels_to_one_hot(labels).to(device)
                
                image_features = model.encode_image(images)
                outputs = model.classifier(image_features)
                loss = criterion(outputs, labels)
                test_loss += loss.item()
        
        test_loss /= len(test_loader)
        print(f"Test Loss: {test_loss:.4f}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="模型训练工具")
    parser.add_argument("--dataset_dir", type=str, required=True, help="数据集目录路径")
    parser.add_argument("--annotations_file", type=str, required=True, help="标注结果文件路径")
    parser.add_argument("--output_dir", type=str, default="models/finetuned", help="模型输出目录")
    parser.add_argument("--epochs", type=int, default=50, help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=32, help="批处理大小")
    parser.add_argument("--lr", type=float, default=1e-4, help="学习率")
    
    args = parser.parse_args()
    
    # 创建模型训练器
    trainer = CustomTrainer(args.dataset_dir, args.annotations_file, args.output_dir)
    
    # 训练模型
    trainer.train(args.epochs, args.batch_size, args.lr)
    
    print("模型训练完成！")

if __name__ == "__main__":
    import sys
    from typing import List, Dict
    main()
