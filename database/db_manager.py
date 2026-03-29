#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库管理器模块
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional

class DBManager:
    """数据库管理器类"""
    
    def __init__(self, db_path: str = "video_manager.db"):
        """初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建视频表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建标签表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        ''')
        
        # 创建视频-标签关联表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_tags (
            video_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY (video_id) REFERENCES videos (id),
            FOREIGN KEY (tag_id) REFERENCES tags (id),
            PRIMARY KEY (video_id, tag_id)
        )
        ''')
        
        # 创建视频元数据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_metadata (
            video_id INTEGER PRIMARY KEY,
            clip_tags TEXT,
            audio_transcription TEXT,
            audio_keywords TEXT,
            ocr_text TEXT,
            ocr_keywords TEXT,
            clothes_tags TEXT,
            thumbnail_paths TEXT,
            FOREIGN KEY (video_id) REFERENCES videos (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_video(self, path: str, name: str) -> int:
        """添加视频
        
        Args:
            path: 视频路径
            name: 视频名称
            
        Returns:
            视频ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO videos (path, name) VALUES (?, ?)",
                (path, name)
            )
            video_id = cursor.lastrowid
            conn.commit()
            return video_id
        except sqlite3.IntegrityError:
            # 视频已存在，返回现有ID
            cursor.execute(
                "SELECT id FROM videos WHERE path = ?",
                (path,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    def add_tags(self, tags: List[str]) -> Dict[str, int]:
        """添加标签
        
        Args:
            tags: 标签列表
            
        Returns:
            标签名称到ID的映射
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        tag_map = {}
        
        for tag in tags:
            try:
                cursor.execute(
                    "INSERT INTO tags (name) VALUES (?)",
                    (tag,)
                )
                tag_map[tag] = cursor.lastrowid
            except sqlite3.IntegrityError:
                # 标签已存在，返回现有ID
                cursor.execute(
                    "SELECT id FROM tags WHERE name = ?",
                    (tag,)
                )
                result = cursor.fetchone()
                if result:
                    tag_map[tag] = result[0]
        
        conn.commit()
        conn.close()
        return tag_map
    
    def add_video_tags(self, video_id: int, tag_ids: List[int]):
        """添加视频-标签关联
        
        Args:
            video_id: 视频ID
            tag_ids: 标签ID列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 先删除现有关联
        cursor.execute(
            "DELETE FROM video_tags WHERE video_id = ?",
            (video_id,)
        )
        
        # 添加新关联
        for tag_id in tag_ids:
            cursor.execute(
                "INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)",
                (video_id, tag_id)
            )
        
        conn.commit()
        conn.close()
    
    def add_video_metadata(self, video_id: int, metadata: Dict):
        """添加视频元数据
        
        Args:
            video_id: 视频ID
            metadata: 元数据字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 准备数据
        clip_tags = json.dumps(metadata.get("clip_tags", []))
        audio_transcription = metadata.get("audio_transcription", "")
        audio_keywords = json.dumps(metadata.get("audio_keywords", []))
        ocr_text = metadata.get("ocr_text", "")
        ocr_keywords = json.dumps(metadata.get("ocr_keywords", []))
        clothes_tags = json.dumps(metadata.get("clothes_tags", []))
        thumbnail_paths = json.dumps(metadata.get("thumbnail_paths", []))
        
        # 检查是否已存在元数据
        cursor.execute(
            "SELECT 1 FROM video_metadata WHERE video_id = ?",
            (video_id,)
        )
        
        if cursor.fetchone():
            # 更新现有元数据
            cursor.execute('''
            UPDATE video_metadata SET
                clip_tags = ?,
                audio_transcription = ?,
                audio_keywords = ?,
                ocr_text = ?,
                ocr_keywords = ?,
                clothes_tags = ?,
                thumbnail_paths = ?
            WHERE video_id = ?
            ''', (
                clip_tags, audio_transcription, audio_keywords,
                ocr_text, ocr_keywords, clothes_tags, thumbnail_paths,
                video_id
            ))
        else:
            # 插入新元数据
            cursor.execute('''
            INSERT INTO video_metadata (
                video_id, clip_tags, audio_transcription, audio_keywords,
                ocr_text, ocr_keywords, clothes_tags, thumbnail_paths
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_id, clip_tags, audio_transcription, audio_keywords,
                ocr_text, ocr_keywords, clothes_tags, thumbnail_paths
            ))
        
        conn.commit()
        conn.close()
    
    def get_video_by_id(self, video_id: int) -> Optional[Dict]:
        """根据ID获取视频信息
        
        Args:
            video_id: 视频ID
            
        Returns:
            视频信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取视频基本信息
        cursor.execute(
            "SELECT id, path, name, created_at FROM videos WHERE id = ?",
            (video_id,)
        )
        video = cursor.fetchone()
        
        if not video:
            conn.close()
            return None
        
        video_info = {
            "id": video[0],
            "path": video[1],
            "name": video[2],
            "created_at": video[3]
        }
        
        # 获取标签
        cursor.execute('''
        SELECT t.name FROM tags t
        JOIN video_tags vt ON t.id = vt.tag_id
        WHERE vt.video_id = ?
        ''', (video_id,))
        tags = [row[0] for row in cursor.fetchall()]
        video_info["tags"] = tags
        
        # 获取元数据
        cursor.execute(
            "SELECT clip_tags, audio_transcription, audio_keywords, ocr_text, ocr_keywords, clothes_tags, thumbnail_paths FROM video_metadata WHERE video_id = ?",
            (video_id,)
        )
        metadata = cursor.fetchone()
        
        if metadata:
            video_info["metadata"] = {
                "clip_tags": json.loads(metadata[0]) if metadata[0] else [],
                "audio_transcription": metadata[1],
                "audio_keywords": json.loads(metadata[2]) if metadata[2] else [],
                "ocr_text": metadata[3],
                "ocr_keywords": json.loads(metadata[4]) if metadata[4] else [],
                "clothes_tags": json.loads(metadata[5]) if metadata[5] else [],
                "thumbnail_paths": json.loads(metadata[6]) if metadata[6] else []
            }
        
        conn.close()
        return video_info
    
    def search_videos_by_tags(self, tags: List[str]) -> List[Dict]:
        """根据标签搜索视频
        
        Args:
            tags: 标签列表
            
        Returns:
            视频信息列表
        """
        if not tags:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询
        placeholders = ",".join(["?"] * len(tags))
        query = f'''
        SELECT v.id, v.path, v.name, v.created_at
        FROM videos v
        JOIN video_tags vt ON v.id = vt.video_id
        JOIN tags t ON vt.tag_id = t.id
        WHERE t.name IN ({placeholders})
        GROUP BY v.id
        HAVING COUNT(DISTINCT t.name) = {len(tags)}
        '''
        
        cursor.execute(query, tags)
        videos = cursor.fetchall()
        
        result = []
        for video in videos:
            video_info = {
                "id": video[0],
                "path": video[1],
                "name": video[2],
                "created_at": video[3]
            }
            
            # 获取视频标签
            cursor.execute('''
            SELECT t.name FROM tags t
            JOIN video_tags vt ON t.id = vt.tag_id
            WHERE vt.video_id = ?
            ''', (video[0],))
            video_info["tags"] = [row[0] for row in cursor.fetchall()]
            
            result.append(video_info)
        
        conn.close()
        return result
    
    def get_all_videos(self) -> List[Dict]:
        """获取所有视频
        
        Returns:
            视频信息列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, path, name, created_at FROM videos")
        videos = cursor.fetchall()
        
        result = []
        for video in videos:
            video_info = {
                "id": video[0],
                "path": video[1],
                "name": video[2],
                "created_at": video[3]
            }
            
            # 获取视频标签
            cursor.execute('''
            SELECT t.name FROM tags t
            JOIN video_tags vt ON t.id = vt.tag_id
            WHERE vt.video_id = ?
            ''', (video[0],))
            video_info["tags"] = [row[0] for row in cursor.fetchall()]
            
            result.append(video_info)
        
        conn.close()
        return result
    
    def delete_video(self, video_id: int) -> bool:
        """删除视频记录
        
        Args:
            video_id: 视频ID
            
        Returns:
            是否删除成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 开始事务
            conn.execute('BEGIN TRANSACTION')
            
            # 删除视频-标签关联
            cursor.execute("DELETE FROM video_tags WHERE video_id = ?", (video_id,))
            
            # 删除视频元数据
            cursor.execute("DELETE FROM video_metadata WHERE video_id = ?", (video_id,))
            
            # 删除视频记录
            cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            
            # 提交事务
            conn.execute('COMMIT')
            return True
        except Exception:
            # 回滚事务
            conn.execute('ROLLBACK')
            return False
        finally:
            conn.close()
    
    def add_feedback(self, video_id: int, original_tags: List[str], corrected_tags: List[str]):
        """添加用户反馈
        
        Args:
            video_id: 视频ID
            original_tags: 原始标签
            corrected_tags: 用户纠正后的标签
        """
        # 创建反馈表（如果不存在）
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER,
            original_tags TEXT,
            corrected_tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos (id)
        )
        ''')
        
        # 插入反馈数据
        cursor.execute(
            "INSERT INTO feedback (video_id, original_tags, corrected_tags) VALUES (?, ?, ?)",
            (video_id, str(original_tags), str(corrected_tags))
        )
        
        conn.commit()
        conn.close()