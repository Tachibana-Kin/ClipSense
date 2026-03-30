#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缩略图生成器模块
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple
from utils.config_manager import ConfigManager

class ThumbnailGenerator:
    """缩略图生成器类"""
    
    def __init__(self):
        """初始化缩略图生成器"""
        self.config_manager = ConfigManager()
    
    def is_black_frame(self, frame: np.ndarray, threshold: int = 10, ratio: float = 0.9) -> bool:
        """判断是否为黑屏帧
        
        Args:
            frame: 视频帧
            threshold: 亮度阈值
            ratio: 黑色像素比例阈值
            
        Returns:
            是否为黑屏帧
        """
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 计算黑色像素比例
        black_pixels = np.sum(gray < threshold)
        total_pixels = gray.size
        black_ratio = black_pixels / total_pixels
        
        return black_ratio > ratio
    
    def calculate_frame_score(self, frame: np.ndarray) -> float:
        """计算帧的质量分数
        
        Args:
            frame: 视频帧
            
        Returns:
            帧质量分数
        """
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 计算亮度均值
        brightness = np.mean(gray)
        
        # 计算边缘强度
        edges = cv2.Canny(gray, 100, 200)
        edge_strength = np.sum(edges) / edges.size
        
        # 计算纹理复杂度
        texture = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # 综合评分
        score = brightness * 0.3 + edge_strength * 0.4 + texture * 0.3
        
        return score
    
    def select_representative_frames(self, video_path: str, num_frames: int = None) -> List[Tuple[int, np.ndarray]]:
        """选择视频的代表帧
        
        Args:
            video_path: 视频文件路径
            num_frames: 要选择的代表帧数（默认使用配置）
            
        Returns:
            代表帧列表，每个元素为(帧索引, 帧)元组
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise Exception(f"无法打开视频文件: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # 使用配置中的设置
        if num_frames is None:
            num_frames = self.config_manager.get_thumbnail_count()
        
        # 计算截图间隔的帧数
        interval_minutes = self.config_manager.get_thumbnail_interval()
        interval_frames = int(fps * interval_minutes * 60)  # 转换为秒
        
        frame_candidates = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % interval_frames == 0:
                # 跳过黑屏帧
                if not self.is_black_frame(frame):
                    score = self.calculate_frame_score(frame)
                    frame_candidates.append((score, frame_count, frame))
            
            frame_count += 1
        
        cap.release()
        
        # 如果候选帧数量不足，使用所有候选帧
        if len(frame_candidates) < num_frames:
            selected_frames = [(frame_idx, frame) for _, frame_idx, frame in frame_candidates]
        else:
            # 按分数排序并选择前N个
            frame_candidates.sort(key=lambda x: x[0], reverse=True)
            selected_frames = [(frame_idx, frame) for _, frame_idx, frame in frame_candidates[:num_frames]]
        
        # 按帧索引排序
        selected_frames.sort(key=lambda x: x[0])
        
        return selected_frames
    
    def generate_thumbnail(self, frame: np.ndarray, size: Tuple[int, int] = None) -> np.ndarray:
        """生成缩略图
        
        Args:
            frame: 视频帧
            size: 缩略图尺寸（默认None，保持原始分辨率）
            
        Returns:
            缩略图
        """
        # 保持原始分辨率
        if size is None:
            return frame
        # 如果指定了尺寸，则进行缩放
        return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
    
    def save_thumbnails(self, video_path: str, output_dir: str, num_thumbnails: int = 5, frames: List[str] = None) -> List[str]:
        """保存视频的缩略图
        
        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            num_thumbnails: 要生成的缩略图数量
            frames: 已提取的帧文件路径列表（可选）
            
        Returns:
            缩略图文件路径列表
        """
        import hashlib
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        print(f"保存缩略图到目录: {output_dir}")
        
        # 保存缩略图
        thumbnail_paths = []
        
        # 使用视频路径的哈希值作为文件名的一部分，确保文件名安全
        video_hash = hashlib.md5(video_path.encode()).hexdigest()[:8]
        
        if frames:
            print(f"使用已提取的帧，数量: {len(frames)}")
            # 使用已提取的帧
            for i, frame_path in enumerate(frames[:num_thumbnails]):
                print(f"处理帧: {frame_path}")
                frame = cv2.imread(frame_path)
                if frame is not None:
                    print(f"读取帧成功，形状: {frame.shape}")
                    thumbnail = self.generate_thumbnail(frame, size=None)
                    # 使用哈希值作为文件名，避免编码问题
                    thumbnail_path = os.path.abspath(os.path.join(output_dir, f"thumbnail_{video_hash}_{i+1}.jpg"))
                    print(f"保存缩略图到: {thumbnail_path}")
                    # 使用配置中的压缩质量
                    quality = self.config_manager.get_thumbnail_quality()
                    success = cv2.imwrite(thumbnail_path, thumbnail, [cv2.IMWRITE_JPEG_QUALITY, quality])
                    print(f"cv2.imwrite 返回值: {success}")
                    if success and os.path.exists(thumbnail_path):
                        print(f"缩略图保存成功，文件大小: {os.path.getsize(thumbnail_path)} bytes")
                        thumbnail_paths.append(thumbnail_path)
                    else:
                        print(f"缩略图保存失败")
                else:
                    print(f"读取帧失败: {frame_path}")
        else:
            print("使用代表帧")
            # 选择代表帧
            representative_frames = self.select_representative_frames(video_path, num_thumbnails)
            print(f"选择了 {len(representative_frames)} 个代表帧")
            
            for i, (frame_idx, frame) in enumerate(representative_frames):
                print(f"处理代表帧: {frame_idx}")
                thumbnail = self.generate_thumbnail(frame, size=None)
                # 使用哈希值作为文件名，避免编码问题
                thumbnail_path = os.path.abspath(os.path.join(output_dir, f"thumbnail_{video_hash}_{i+1}.jpg"))
                print(f"保存缩略图到: {thumbnail_path}")
                # 使用配置中的压缩质量
                quality = self.config_manager.get_thumbnail_quality()
                success = cv2.imwrite(thumbnail_path, thumbnail, [cv2.IMWRITE_JPEG_QUALITY, quality])
                print(f"cv2.imwrite 返回值: {success}")
                if success and os.path.exists(thumbnail_path):
                    print(f"缩略图保存成功，文件大小: {os.path.getsize(thumbnail_path)} bytes")
                    thumbnail_paths.append(thumbnail_path)
                else:
                    print(f"缩略图保存失败")
        
        print(f"生成的缩略图路径: {thumbnail_paths}")
        return thumbnail_paths