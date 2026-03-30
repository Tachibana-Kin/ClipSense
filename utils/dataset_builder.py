#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据集构建工具
"""

import os
import shutil
import random
import argparse
import cv2
from pathlib import Path
from typing import List, Tuple
from video_processor.video_analyzer import VideoAnalyzer
from utils.thumbnail_generator import ThumbnailGenerator

class DatasetBuilder:
    """数据集构建器类"""
    
    def __init__(self, output_dir: str):
        """初始化数据集构建器
        
        Args:
            output_dir: 数据集输出目录
        """
        self.output_dir = output_dir
        self.thumbnail_generator = ThumbnailGenerator()
        self.train_dir = os.path.join(output_dir, "train")
        self.val_dir = os.path.join(output_dir, "val")
        self.test_dir = os.path.join(output_dir, "test")
        
        # 创建目录结构
        for dir_path in [self.train_dir, self.val_dir, self.test_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def extract_frames_from_video(self, video_path: str, num_frames: int = 30) -> List[str]:
        """从视频中提取帧
        
        Args:
            video_path: 视频文件路径
            num_frames: 提取的帧数量
            
        Returns:
            提取的帧文件路径列表
        """
        print(f"正在从视频中提取帧: {video_path}")
        
        # 使用缩略图生成器提取代表帧
        frames = self.thumbnail_generator.select_representative_frames(video_path, num_frames)
        
        # 为每个视频创建唯一的临时子目录（使用数字ID避免中文路径问题）
        import hashlib
        video_hash = hashlib.md5(video_path.encode()).hexdigest()[:8]
        temp_dir = os.path.join(self.output_dir, "temp_frames", video_hash)
        os.makedirs(temp_dir, exist_ok=True)
        print(f"临时目录: {temp_dir}")
        
        frame_paths = []
        for i, (frame_idx, frame) in enumerate(frames):
            try:
                # 使用简单的数字文件名，避免任何字符问题
                safe_filename = f"frame_{i:06d}.jpg"
                frame_path = os.path.join(temp_dir, safe_filename)
                print(f"保存帧到: {frame_path}")
                
                # 确保目录存在
                os.makedirs(os.path.dirname(frame_path), exist_ok=True)
                
                # 保存帧
                success = cv2.imwrite(frame_path, frame)
                if success:
                    print(f"成功保存帧: {frame_path}")
                    frame_paths.append(frame_path)
                else:
                    print(f"保存帧失败: {frame_path}")
                    # 尝试使用绝对路径
                    abs_frame_path = os.path.abspath(frame_path)
                    print(f"尝试使用绝对路径: {abs_frame_path}")
                    success = cv2.imwrite(abs_frame_path, frame)
                    if success:
                        print(f"使用绝对路径成功保存帧: {abs_frame_path}")
                        frame_paths.append(abs_frame_path)
                    else:
                        print(f"使用绝对路径也保存失败")
            except Exception as e:
                print(f"处理帧 {i} 失败: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"成功提取 {len(frame_paths)} 帧")
        return frame_paths
    
    def process_video_directory(self, video_dir: str, num_frames_per_video: int = 30):
        """处理视频目录，提取所有视频的帧
        
        Args:
            video_dir: 视频目录路径
            num_frames_per_video: 每个视频提取的帧数量
        """
        print(f"正在处理视频目录: {video_dir}")
        
        # 获取所有视频文件
        video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
        video_files = []
        
        for root, _, files in os.walk(video_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    video_files.append(os.path.join(root, file))
        
        print(f"找到 {len(video_files)} 个视频文件")
        
        # 提取每个视频的帧
        all_frames = []
        for video_path in video_files:
            try:
                frames = self.extract_frames_from_video(video_path, num_frames_per_video)
                all_frames.extend(frames)
                print(f"成功提取 {len(frames)} 帧")
            except Exception as e:
                print(f"处理视频 {video_path} 失败: {e}")
        
        print(f"总共提取 {len(all_frames)} 帧")
        return all_frames
    
    def split_dataset(self, frames: List[str], train_ratio: float = 0.7, val_ratio: float = 0.15):
        """按比例划分数据集
        
        Args:
            frames: 帧文件路径列表
            train_ratio: 训练集比例
            val_ratio: 验证集比例
        """
        print(f"正在划分数据集，总帧数: {len(frames)}")
        
        # 随机打乱帧顺序
        random.shuffle(frames)
        
        # 计算划分数量
        total_frames = len(frames)
        train_count = int(total_frames * train_ratio)
        val_count = int(total_frames * val_ratio)
        test_count = total_frames - train_count - val_count
        
        print(f"训练集: {train_count} 帧, 验证集: {val_count} 帧, 测试集: {test_count} 帧")
        
        # 划分帧
        train_frames = frames[:train_count]
        val_frames = frames[train_count:train_count+val_count]
        test_frames = frames[train_count+val_count:]
        
        # 复制到对应目录
        self._copy_frames(train_frames, self.train_dir)
        self._copy_frames(val_frames, self.val_dir)
        self._copy_frames(test_frames, self.test_dir)
        
        print("数据集划分完成")
    
    def _copy_frames(self, frames: List[str], target_dir: str):
        """将帧复制到目标目录
        
        Args:
            frames: 帧文件路径列表
            target_dir: 目标目录
        """
        # 获取目标目录中已有的文件数量，确保新文件从正确的序号开始
        existing_files = [f for f in os.listdir(target_dir) if f.startswith("frame_") and f.endswith(".jpg")]
        start_idx = len(existing_files)
        
        for i, frame_path in enumerate(frames):
            try:
                # 确保目标目录存在
                os.makedirs(target_dir, exist_ok=True)
                
                # 按顺序重命名文件，确保帧是按顺序保存的
                # 使用全局序号，避免覆盖已有文件
                dest_filename = f"frame_{start_idx + i:06d}.jpg"
                dest_path = os.path.join(target_dir, dest_filename)
                shutil.copy2(frame_path, dest_path)
                print(f"复制帧: {frame_path} -> {dest_path}")
            except Exception as e:
                print(f"复制帧 {frame_path} 失败: {e}")
    
    def clean_temp_files(self):
        """清理临时文件"""
        temp_dir = os.path.join(self.output_dir, "temp_frames")
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print("临时文件清理完成")
            except Exception as e:
                print(f"清理临时文件失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据集构建工具")
    parser.add_argument("--video_dir", type=str, required=True, help="视频目录路径")
    parser.add_argument("--output_dir", type=str, default="dataset", help="数据集输出目录")
    parser.add_argument("--num_frames", type=int, default=30, help="每个视频提取的帧数量")
    parser.add_argument("--train_ratio", type=float, default=0.7, help="训练集比例")
    parser.add_argument("--val_ratio", type=float, default=0.15, help="验证集比例")
    
    args = parser.parse_args()
    
    # 创建数据集构建器
    builder = DatasetBuilder(args.output_dir)
    
    # 处理视频目录
    frames = builder.process_video_directory(args.video_dir, args.num_frames)
    
    # 划分数据集
    builder.split_dataset(frames, args.train_ratio, args.val_ratio)
    
    # 清理临时文件
    builder.clean_temp_files()
    
    print("数据集构建完成！")

if __name__ == "__main__":
    import cv2
    main()
