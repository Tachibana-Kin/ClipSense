#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频分析器模块
"""

import os
import cv2
import tempfile
from pathlib import Path
from typing import List, Tuple, Dict
from models.clip_model import CLIPModel
from models.whisper_model import WhisperModel
from models.ocr_model import OCRModel
from models.clothes_model import ClothesModel
from utils.tag_manager import TagManager
from utils.thumbnail_generator import ThumbnailGenerator
from utils.file_renamer import FileRenamer
from database.db_manager import DBManager

class VideoAnalyzer:
    """视频分析器类"""
    
    def __init__(self, video_path: str):
        """初始化视频分析器
        
        Args:
            video_path: 视频文件路径
        """
        self.video_path = video_path
        self.video_name = Path(video_path).name
        # 创建安全的临时目录
        self.temp_dir = tempfile.mkdtemp(prefix='video_analyzer_')
        # 设置适当的权限（仅当前用户可访问）
        import os
        os.chmod(self.temp_dir, 0o700)
        self.clip_model = CLIPModel()
        self.whisper_model = WhisperModel()
        self.ocr_model = OCRModel()
        self.clothes_model = ClothesModel()
        self.tag_manager = TagManager()
        self.thumbnail_generator = ThumbnailGenerator()
        self.file_renamer = FileRenamer()
        self.db_manager = DBManager()
        
    def extract_frames(self, frame_interval: int = 10) -> List[str]:
        """从视频中提取帧
        
        Args:
            frame_interval: 帧间隔，每多少帧提取一帧
            
        Returns:
            提取的帧文件路径列表
        """
        frames = []
        cap = cv2.VideoCapture(self.video_path)
        
        if not cap.isOpened():
            raise Exception(f"无法打开视频文件: {self.video_path}")
        
        frame_count = 0
        extracted_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                frame_path = os.path.join(self.temp_dir, f"frame_{extracted_count}.jpg")
                cv2.imwrite(frame_path, frame)
                frames.append(frame_path)
                extracted_count += 1
            
            frame_count += 1
        
        cap.release()
        return frames
    
    def get_video_info(self) -> dict:
        """获取视频信息
        
        Returns:
            视频信息字典
        """
        cap = cv2.VideoCapture(self.video_path)
        
        if not cap.isOpened():
            raise Exception(f"无法打开视频文件: {self.video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        cap.release()
        
        return {
            "fps": fps,
            "total_frames": total_frames,
            "width": width,
            "height": height
        }
    
    def analyze_frames_with_clip(self, frames: List[str]) -> List[Dict[str, float]]:
        """使用CLIP模型分析视频帧
        
        Args:
            frames: 帧文件路径列表
            
        Returns:
            合并后的标签及其置信度列表
        """
        all_labels = {}
        
        # 分析每个帧
        for frame_path in frames:
            frame_labels = self.clip_model.predict(frame_path)
            for label_info in frame_labels:
                label = label_info["label"]
                confidence = label_info["confidence"]
                
                if label in all_labels:
                    all_labels[label] = max(all_labels[label], confidence)
                else:
                    all_labels[label] = confidence
        
        # 转换为列表并排序
        result = [
            {"label": label, "confidence": confidence}
            for label, confidence in all_labels.items()
        ]
        result.sort(key=lambda x: x["confidence"], reverse=True)
        
        return result[:10]  # 返回前10个最可能的标签
    
    def analyze_audio_with_whisper(self) -> Dict:
        """使用Whisper模型分析视频音频
        
        Returns:
            音频分析结果字典
        """
        # 转录音频
        transcription = self.whisper_model.transcribe(self.video_path)
        
        # 提取关键词
        keywords = self.whisper_model.extract_keywords(transcription["text"])
        
        return {
            "transcription": transcription["text"],
            "keywords": keywords
        }
    
    def analyze_frames_with_ocr(self, frames: List[str]) -> Dict:
        """使用OCR模型分析视频帧中的文字
        
        Args:
            frames: 帧文件路径列表
            
        Returns:
            OCR分析结果字典
        """
        all_text = ""
        all_keywords = set()
        
        # 分析每个帧
        for frame_path in frames:
            ocr_result = self.ocr_model.recognize(frame_path)
            all_text += ocr_result["text"] + "\n"
            all_keywords.update(ocr_result["keywords"])
        
        return {
            "text": all_text.strip(),
            "keywords": list(all_keywords)
        }
    
    def analyze_frames_with_clothes(self, frames: List[str]) -> List[Dict[str, float]]:
        """使用服饰识别模型分析视频帧中的服饰
        
        Args:
            frames: 帧文件路径列表
            
        Returns:
            服饰标签及其置信度列表
        """
        all_clothes = {}
        
        # 分析每个帧
        for frame_path in frames:
            clothes_result = self.clothes_model.recognize(frame_path)
            for clothes_info in clothes_result:
                label = clothes_info["label"]
                confidence = clothes_info["confidence"]
                
                if label in all_clothes:
                    all_clothes[label] = max(all_clothes[label], confidence)
                else:
                    all_clothes[label] = confidence
        
        # 转换为列表并排序
        result = [
            {"label": label, "confidence": confidence}
            for label, confidence in all_clothes.items()
        ]
        result.sort(key=lambda x: x["confidence"], reverse=True)
        
        return result[:5]  # 返回前5个最可能的服饰标签
    
    def analyze_video(self) -> Dict:
        """综合分析视频
        
        Returns:
            综合分析结果
        """
        # 提取帧（每2-3分钟提取一帧，假设30fps）
        # 2分钟 = 30fps * 120秒 = 3600帧
        frames = self.extract_frames(frame_interval=3600)  # 每2分钟提取一帧
        
        # 分析视觉内容
        clip_tags = self.analyze_frames_with_clip(frames)
        
        # 分析音频
        audio_result = self.analyze_audio_with_whisper()
        
        # 分析文字
        ocr_result = self.analyze_frames_with_ocr(frames)
        
        # 分析服饰
        clothes_tags = self.analyze_frames_with_clothes(frames)
        
        # 融合标签
        merged_tags = self.tag_manager.merge_tags(
            clip_tags, 
            audio_result["keywords"], 
            ocr_result["keywords"], 
            clothes_tags
        )
        
        return {
            "video_path": self.video_path,
            "video_name": self.video_name,
            "clip_tags": clip_tags,
            "audio_transcription": audio_result["transcription"],
            "audio_keywords": audio_result["keywords"],
            "ocr_text": ocr_result["text"],
            "ocr_keywords": ocr_result["keywords"],
            "clothes_tags": clothes_tags,
            "merged_tags": merged_tags,
            "frames": frames  # 返回提取的帧，用于缩略图生成
        }
    
    # 标签管理方法
    def add_tag(self, tag: str) -> bool:
        """添加标签
        
        Args:
            tag: 要添加的标签
            
        Returns:
            是否添加成功
        """
        return self.tag_manager.add_tag(tag)
    
    def remove_tag(self, tag: str) -> bool:
        """删除标签
        
        Args:
            tag: 要删除的标签
            
        Returns:
            是否删除成功
        """
        return self.tag_manager.remove_tag(tag)
    
    def update_tag(self, old_tag: str, new_tag: str) -> bool:
        """更新标签
        
        Args:
            old_tag: 旧标签
            new_tag: 新标签
            
        Returns:
            是否更新成功
        """
        return self.tag_manager.update_tag(old_tag, new_tag)
    
    def get_tags(self) -> List[str]:
        """获取所有标签
        
        Returns:
            标签列表
        """
        return self.tag_manager.get_tags()
    
    def generate_thumbnails(self, output_dir: str = None, num_thumbnails: int = 3, frames: List[str] = None) -> List[str]:
        """生成视频缩略图
        
        Args:
            output_dir: 输出目录（默认使用工程目录下的thumbnails）
            num_thumbnails: 要生成的缩略图数量
            frames: 已提取的帧文件路径列表（可选）
            
        Returns:
            缩略图文件路径列表
        """
        if output_dir is None:
            # 使用工程目录下的thumbnails文件夹
            self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(self.project_dir, "thumbnails")
        return self.thumbnail_generator.save_thumbnails(self.video_path, output_dir, num_thumbnails, frames)
    
    def rename_file(self, tags: List[str]) -> str:
        """重命名视频文件
        
        Args:
            tags: 标签列表
            
        Returns:
            新的文件路径
        """
        new_path = self.file_renamer.rename_file(self.video_path, tags)
        # 更新视频路径
        self.video_path = new_path
        self.video_name = Path(new_path).name
        return new_path
    
    def save_to_database(self, analysis_result: Dict, thumbnail_paths: List[str]):
        """将视频信息保存到数据库
        
        Args:
            analysis_result: 分析结果
            thumbnail_paths: 缩略图路径列表
        """
        # 添加视频
        video_id = self.db_manager.add_video(self.video_path, self.video_name)
        
        # 添加标签
        tags = analysis_result.get("merged_tags", [])
        tag_map = self.db_manager.add_tags(tags)
        tag_ids = list(tag_map.values())
        
        # 添加视频-标签关联
        self.db_manager.add_video_tags(video_id, tag_ids)
        
        # 准备元数据
        metadata = {
            "clip_tags": analysis_result.get("clip_tags", []),
            "audio_transcription": analysis_result.get("audio_transcription", ""),
            "audio_keywords": analysis_result.get("audio_keywords", []),
            "ocr_text": analysis_result.get("ocr_text", ""),
            "ocr_keywords": analysis_result.get("ocr_keywords", []),
            "clothes_tags": analysis_result.get("clothes_tags", []),
            "thumbnail_paths": thumbnail_paths
        }
        
        # 添加元数据
        self.db_manager.add_video_metadata(video_id, metadata)
    
    def cleanup(self):
        """清理临时文件"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)