#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据集构建和模型训练主脚本
"""

import os
import argparse
from utils.dataset_builder import DatasetBuilder
from utils.semi_auto_annotator import SemiAutoAnnotator
from utils.custom_trainer import CustomTrainer

class TrainCustomModel:
    """自定义模型训练类"""
    
    def __init__(self, video_dir: str, output_dir: str):
        """初始化
        
        Args:
            video_dir: 视频目录路径
            output_dir: 输出目录路径
        """
        self.video_dir = video_dir
        self.output_dir = output_dir
        
        # 创建目录结构
        self.dataset_dir = os.path.join(output_dir, "dataset")
        self.annotations_dir = os.path.join(output_dir, "annotations")
        self.models_dir = os.path.join(output_dir, "models")
        
        for dir_path in [self.dataset_dir, self.annotations_dir, self.models_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def build_dataset(self, num_frames_per_video: int = 30, train_ratio: float = 0.7, val_ratio: float = 0.15):
        """构建数据集
        
        Args:
            num_frames_per_video: 每个视频提取的帧数量
            train_ratio: 训练集比例
            val_ratio: 验证集比例
        """
        print("=== 开始构建数据集 ===")
        
        # 创建数据集构建器
        builder = DatasetBuilder(self.dataset_dir)
        
        # 处理视频
        if os.path.isfile(self.video_dir):
            # 处理单个视频文件
            frames = builder.extract_frames_from_video(self.video_dir, num_frames_per_video)
        else:
            # 处理视频目录
            frames = builder.process_video_directory(self.video_dir, num_frames_per_video)
        
        # 划分数据集
        builder.split_dataset(frames, train_ratio, val_ratio)
        
        # 清理临时文件
        builder.clean_temp_files()
        
        print("=== 数据集构建完成 ===")
    
    def annotate_dataset(self, confidence_threshold: float = 0.5):
        """半自动标注数据集
        
        Args:
            confidence_threshold: 置信度阈值
        """
        print("=== 开始半自动标注 ===")
        
        # 创建半自动标注器
        annotator = SemiAutoAnnotator(self.dataset_dir, self.annotations_dir)
        
        # 处理数据集
        annotator.process_dataset(confidence_threshold)
        
        print("=== 半自动标注完成 ===")
        print("请使用LabelImg手动修正标注，然后继续训练")
    
    def train_model(self, epochs: int = 50, batch_size: int = 32, lr: float = 1e-4):
        """训练模型
        
        Args:
            epochs: 训练轮数
            batch_size: 批处理大小
            lr: 学习率
        """
        print("=== 开始模型训练 ===")
        
        # 标注结果文件
        annotations_file = os.path.join(self.annotations_dir, "annotations.json")
        
        if not os.path.exists(annotations_file):
            print(f"标注文件不存在: {annotations_file}")
            print("请先运行标注步骤")
            return
        
        # 创建模型训练器
        trainer = CustomTrainer(self.dataset_dir, annotations_file, self.models_dir)
        
        # 训练模型
        trainer.train(epochs, batch_size, lr)
        
        print("=== 模型训练完成 ===")
    
    def run_full_pipeline(self, num_frames_per_video: int = 30, train_ratio: float = 0.7, 
                         val_ratio: float = 0.15, confidence_threshold: float = 0.5, 
                         epochs: int = 50, batch_size: int = 32, lr: float = 1e-4):
        """运行完整流程
        
        Args:
            num_frames_per_video: 每个视频提取的帧数量
            train_ratio: 训练集比例
            val_ratio: 验证集比例
            confidence_threshold: 置信度阈值
            epochs: 训练轮数
            batch_size: 批处理大小
            lr: 学习率
        """
        # 构建数据集
        self.build_dataset(num_frames_per_video, train_ratio, val_ratio)
        
        # 半自动标注
        self.annotate_dataset(confidence_threshold)
        
        # 等待用户修正标注
        input("请使用LabelImg手动修正标注，完成后按Enter键继续...")
        
        # 训练模型
        self.train_model(epochs, batch_size, lr)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据集构建和模型训练主脚本")
    parser.add_argument("--video_dir", type=str, required=True, help="视频目录路径")
    parser.add_argument("--output_dir", type=str, default="custom_model", help="输出目录路径")
    parser.add_argument("--num_frames", type=int, default=30, help="每个视频提取的帧数量")
    parser.add_argument("--train_ratio", type=float, default=0.7, help="训练集比例")
    parser.add_argument("--val_ratio", type=float, default=0.15, help="验证集比例")
    parser.add_argument("--confidence_threshold", type=float, default=0.5, help="置信度阈值")
    parser.add_argument("--epochs", type=int, default=50, help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=32, help="批处理大小")
    parser.add_argument("--lr", type=float, default=1e-4, help="学习率")
    parser.add_argument("--step", type=str, choices=["build", "annotate", "train", "full"], 
                        default="full", help="运行步骤")
    
    args = parser.parse_args()
    
    # 创建训练实例
    trainer = TrainCustomModel(args.video_dir, args.output_dir)
    
    # 根据步骤运行
    if args.step == "build":
        trainer.build_dataset(args.num_frames, args.train_ratio, args.val_ratio)
    elif args.step == "annotate":
        trainer.annotate_dataset(args.confidence_threshold)
    elif args.step == "train":
        trainer.train_model(args.epochs, args.batch_size, args.lr)
    elif args.step == "full":
        trainer.run_full_pipeline(args.num_frames, args.train_ratio, args.val_ratio, 
                                 args.confidence_threshold, args.epochs, args.batch_size, args.lr)
    
    print("任务完成！")

if __name__ == "__main__":
    main()
