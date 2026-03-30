#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主窗口模块
"""

import os
import sys
import sqlite3
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFileDialog, QListWidget, QListWidgetItem, 
    QLabel, QLineEdit, QTextEdit, QGridLayout, QScrollArea,
    QMessageBox, QProgressBar, QMenu, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from video_processor.video_analyzer import VideoAnalyzer
from database.db_manager import DBManager
from utils.dataset_builder import DatasetBuilder
from utils.semi_auto_annotator import SemiAutoAnnotator
from utils.custom_trainer import CustomTrainer

class AnalysisThread(QThread):
    """分析线程"""
    finished = pyqtSignal(dict, list)
    error = pyqtSignal(str)
    
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
    
    def run(self):
        try:
            # 禁用flash attention警告
            import torch
            torch.backends.cuda.enable_flash_sdp(False)
            
            analyzer = VideoAnalyzer(self.video_path)
            
            # 分析视频
            analysis_result = analyzer.analyze_video()
            
            # 生成缩略图（使用已提取的帧）
            frames = analysis_result.get("frames", [])
            thumbnail_paths = analyzer.generate_thumbnails(frames=frames)
            
            # 保存到数据库
            analyzer.save_to_database(analysis_result, thumbnail_paths)
            
            analyzer.cleanup()
            self.finished.emit(analysis_result, thumbnail_paths)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频管理工具")
        self.setGeometry(100, 100, 1000, 800)
        
        self.db_manager = DBManager()
        self.analyzer = None
        self.temp_videos = []  # 存储临时视频列表
        self.analysis_queue = []  # 分析队列
        self.is_analyzing = False  # 是否正在分析
        self.current_queue_item = None  # 当前分析的队列项
        
        self.init_ui()
        self.load_videos()
    
    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧布局
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, 1)
        
        # 视频列表
        self.video_list = QListWidget()
        self.video_list.itemClicked.connect(self.on_video_selected)
        left_layout.addWidget(QLabel("视频列表"))
        left_layout.addWidget(self.video_list)
        
        # 分析队列
        self.queue_list = QListWidget()
        left_layout.addWidget(QLabel("分析队列"))
        left_layout.addWidget(self.queue_list)
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入标签搜索视频...")
        search_button = QPushButton("搜索")
        search_button.clicked.connect(self.on_search)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        left_layout.addLayout(search_layout)
        
        # 右侧布局
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, 3)
        
        # 顶部按钮
        top_buttons = QHBoxLayout()
        
        # 添加视频按钮组
        add_button = QPushButton("添加视频")
        add_menu = QMenu()
        add_file_action = add_menu.addAction("选择单个视频")
        add_file_action.triggered.connect(self.on_add_video)
        add_folder_action = add_menu.addAction("打开文件夹")
        add_folder_action.triggered.connect(self.on_add_folder)
        add_button.setMenu(add_menu)
        
        analyze_button = QPushButton("分析视频")
        analyze_button.clicked.connect(self.on_analyze_video)
        
        # 添加缩略图清理按钮
        clean_button = QPushButton("清理缩略图")
        clean_menu = QMenu()
        clean_unused_action = clean_menu.addAction("清理未使用的缩略图")
        clean_unused_action.triggered.connect(self.on_clean_unused_thumbnails)
        clean_all_action = clean_menu.addAction("清理所有缩略图")
        clean_all_action.triggered.connect(self.on_clean_all_thumbnails)
        clean_button.setMenu(clean_menu)
        
        # 添加模型训练按钮
        model_train_button = QPushButton("模型训练")
        model_train_button.clicked.connect(self.show_model_train_page)
        
        top_buttons.addWidget(add_button)
        top_buttons.addWidget(analyze_button)
        top_buttons.addWidget(clean_button)
        top_buttons.addWidget(model_train_button)
        right_layout.addLayout(top_buttons)
        
        # 为视频列表添加右键菜单
        self.video_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.video_list.customContextMenuRequested.connect(self.on_context_menu)
        
        # 为队列列表添加右键菜单
        self.queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self.on_queue_context_menu)
        
        # 视频信息
        info_layout = QVBoxLayout()
        self.video_info = QTextEdit()
        self.video_info.setReadOnly(True)
        info_layout.addWidget(QLabel("视频信息"))
        info_layout.addWidget(self.video_info)
        right_layout.addLayout(info_layout)
        
        # 标签编辑
        tag_layout = QVBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("输入标签...")
        tag_buttons = QHBoxLayout()
        add_tag_button = QPushButton("添加标签")
        add_tag_button.clicked.connect(self.on_add_tag)
        remove_tag_button = QPushButton("删除标签")
        remove_tag_button.clicked.connect(self.on_remove_tag)
        tag_buttons.addWidget(self.tag_input)
        tag_buttons.addWidget(add_tag_button)
        tag_buttons.addWidget(remove_tag_button)
        self.tag_list = QListWidget()
        self.tag_list.setSelectionMode(QListWidget.ExtendedSelection)  # 支持多选
        tag_layout.addWidget(QLabel("标签"))
        tag_layout.addLayout(tag_buttons)
        tag_layout.addWidget(self.tag_list)
        right_layout.addLayout(tag_layout)
        
        # 缩略图
        thumbnail_layout = QVBoxLayout()
        self.thumbnail_area = QScrollArea()
        self.thumbnail_widget = QWidget()
        self.thumbnail_grid = QGridLayout()
        self.thumbnail_widget.setLayout(self.thumbnail_grid)
        self.thumbnail_area.setWidget(self.thumbnail_widget)
        self.thumbnail_area.setWidgetResizable(True)
        thumbnail_layout.addWidget(QLabel("缩略图"))
        thumbnail_layout.addWidget(self.thumbnail_area)
        right_layout.addLayout(thumbnail_layout)
        
        # 进度条（不显示百分比）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)  # 不显示百分比文本
        right_layout.addWidget(self.progress_bar)
        
        # 模型训练页面
        self.model_train_page = None
        

    
    def load_videos(self):
        """加载视频列表（合并数据库视频和临时视频）"""
        self.video_list.clear()
        
        # 添加数据库中的视频
        videos = self.db_manager.get_all_videos()
        for video in videos:
            item = QListWidgetItem(video["name"])
            item.setData(Qt.UserRole, video)
            self.video_list.addItem(item)
        
        # 添加临时视频（未分析的）
        for video_info in self.temp_videos:
            # 检查是否已经在数据库中
            if not any(v["path"] == video_info["path"] for v in videos):
                item = QListWidgetItem(video_info["name"])
                item.setData(Qt.UserRole, video_info)
                self.video_list.addItem(item)
    
    def on_video_selected(self, item):
        """视频选择事件"""
        video_info = item.data(Qt.UserRole)
        self.display_video_info(video_info)
    
    def display_video_info(self, video_info):
        """显示视频信息"""
        # 显示视频信息
        info_text = f"路径: {video_info['path']}\n"
        info_text += f"名称: {video_info['name']}\n"
        info_text += f"创建时间: {video_info['created_at']}\n"
        self.video_info.setText(info_text)
        
        # 显示标签
        self.tag_list.clear()
        for tag in video_info.get("tags", []):
            self.tag_list.addItem(tag)
        
        # 显示缩略图
        self.clear_thumbnails()
        if "metadata" in video_info:
            thumbnails = video_info["metadata"].get("thumbnail_paths", [])
            self.display_thumbnails(thumbnails)
    
    def clear_thumbnails(self):
        """清除缩略图"""
        for i in reversed(range(self.thumbnail_grid.count())):
            widget = self.thumbnail_grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()
    
    def display_thumbnails(self, thumbnail_paths):
        """显示缩略图（同时显示3张）"""
        print(f"显示缩略图，路径数量: {len(thumbnail_paths)}")
        # 只显示前3张缩略图
        display_paths = thumbnail_paths[:3]
        print(f"实际显示数量: {len(display_paths)}")
        
        for i, path in enumerate(display_paths):
            print(f"缩略图路径: {path}")
            # 转换为绝对路径
            abs_path = os.path.abspath(path)
            print(f"绝对路径: {abs_path}")
            if os.path.exists(abs_path):
                print(f"文件存在: {abs_path}")
                try:
                    pixmap = QPixmap(abs_path)
                    print(f"pixmap创建成功，尺寸: {pixmap.width()}x{pixmap.height()}")
                    if not pixmap.isNull():
                        # 密铺显示，保持原始宽高比
                        label = QLabel()
                        label.setPixmap(pixmap)
                        label.setScaledContents(True)  # 让图片自动缩放填充整个标签
                        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 让标签可以扩展
                        # 一行显示3张，自动调整大小
                        col = i
                        self.thumbnail_grid.addWidget(label, 0, col)
                        print(f"缩略图 {i+1} 添加成功")
                    else:
                        print(f"pixmap为空，无法加载图片: {abs_path}")
                except Exception as e:
                    print(f"显示缩略图失败: {str(e)}")
            else:
                print(f"文件不存在: {abs_path}")
    
    def on_add_video(self):
        """添加视频（只枚举，不自动分析）"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.webm)"
        )
        
        if file_path:
            # 只添加到列表，不自动分析
            video_name = os.path.basename(file_path)
            # 创建临时视频信息
            video_info = {
                "id": None,  # 临时ID
                "path": file_path,
                "name": video_name,
                "created_at": "未分析",
                "tags": [],
                "metadata": {}
            }
            # 添加到临时视频列表
            self.temp_videos.append(video_info)
            # 刷新列表显示
            self.load_videos()
            QMessageBox.information(self, "添加成功", f"视频 '{video_name}' 已添加到列表")
    
    def on_add_folder(self):
        """打开文件夹并读取视频列表"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "选择视频文件夹", ""
        )
        
        if folder_path:
            # 支持的视频格式
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
            video_files = []
            
            # 遍历文件夹
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        video_files.append(os.path.join(root, file))
            
            if video_files:
                # 添加视频文件到临时列表
                for video_path in video_files:
                    video_name = os.path.basename(video_path)
                    # 创建临时视频信息
                    video_info = {
                        "id": None,  # 临时ID
                        "path": video_path,
                        "name": video_name,
                        "created_at": "未分析",
                        "tags": [],
                        "metadata": {}
                    }
                    # 添加到临时视频列表（避免重复）
                    if not any(v["path"] == video_path for v in self.temp_videos):
                        self.temp_videos.append(video_info)
                
                # 刷新列表显示
                self.load_videos()
                QMessageBox.information(self, "导入成功", f"成功导入 {len(video_files)} 个视频文件")
            else:
                QMessageBox.warning(self, "未找到视频", "所选文件夹中没有找到视频文件")
    
    def analyze_video(self, video_path):
        """分析视频"""
        # 添加到分析队列
        video_name = os.path.basename(video_path)
        queue_item = QListWidgetItem(f"待分析: {video_name}")
        queue_item.setData(Qt.UserRole, video_path)
        self.queue_list.addItem(queue_item)
        
        # 如果当前没有正在分析的视频，则开始分析
        if not self.is_analyzing:
            self.process_next_in_queue()
    

    
    def on_analysis_finished(self, analysis_result, thumbnail_paths):
        """分析完成"""
        self.progress_bar.setValue(100)
        QMessageBox.information(self, "分析完成", "视频分析完成！")
        self.progress_bar.setVisible(False)
        
        # 从队列中移除已完成的视频
        video_path = analysis_result.get("video_path")
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            if item.data(Qt.UserRole) == video_path:
                self.queue_list.takeItem(i)
                break
        
        # 从临时列表中移除已分析的视频
        self.temp_videos = [v for v in self.temp_videos if v["path"] != video_path]
        
        # 重新加载视频列表（现在包含已分析的视频）
        self.load_videos()
        
        # 重新选择刚才分析的视频
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            video_info = item.data(Qt.UserRole)
            if video_info.get("path") == video_path:
                self.video_list.setCurrentItem(item)
                self.on_video_selected(item)
                break
    
    def process_next_in_queue(self):
        """处理队列中的下一个视频"""
        if self.queue_list.count() > 0 and not self.is_analyzing:
            # 获取队列中的第一个视频
            self.current_queue_item = self.queue_list.item(0)
            video_path = self.current_queue_item.data(Qt.UserRole)
            video_name = os.path.basename(video_path)
            
            # 显示进度条（不显示百分比）
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 将状态改为分析中
            self.current_queue_item.setText(f"分析中: {video_name}")
            
            # 开始分析
            self.is_analyzing = True
            self.analysis_thread = AnalysisThread(video_path)
            self.analysis_thread.finished.connect(self.on_analysis_finished)
            self.analysis_thread.error.connect(self.on_analysis_error)
            self.analysis_thread.start()
    
    def on_analysis_finished(self, analysis_result, thumbnail_paths):
        """分析完成"""
        self.progress_bar.setValue(100)
        
        # 将当前队列项标记为已完成
        if self.current_queue_item:
            video_name = os.path.basename(self.current_queue_item.data(Qt.UserRole))
            self.current_queue_item.setText(f"已完成: {video_name}")
        
        QMessageBox.information(self, "分析完成", "视频分析完成！")
        self.progress_bar.setVisible(False)
        
        # 从队列中移除已完成的视频
        if self.current_queue_item:
            self.queue_list.takeItem(self.queue_list.row(self.current_queue_item))
            self.current_queue_item = None
        
        # 从临时列表中移除已分析的视频
        video_path = analysis_result.get("video_path")
        self.temp_videos = [v for v in self.temp_videos if v["path"] != video_path]
        
        # 重新加载视频列表（现在包含已分析的视频）
        self.load_videos()
        
        # 重新选择刚才分析的视频
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            video_info = item.data(Qt.UserRole)
            if video_info.get("path") == video_path:
                self.video_list.setCurrentItem(item)
                self.on_video_selected(item)
                break
        
        # 标记分析完成，处理下一个视频
        self.is_analyzing = False
        self.process_next_in_queue()
    
    def on_analysis_error(self, error):
        """分析错误"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "分析错误", f"分析失败: {error}")
        
        # 从队列中移除失败的视频
        if self.current_queue_item:
            self.queue_list.takeItem(self.queue_list.row(self.current_queue_item))
            self.current_queue_item = None
        
        # 标记分析完成，处理下一个视频
        self.is_analyzing = False
        self.process_next_in_queue()
    
    def on_analyze_video(self):
        """分析选中的视频"""
        selected_items = self.video_list.selectedItems()
        if selected_items:
            video_info = selected_items[0].data(Qt.UserRole)
            video_path = video_info["path"]
            if video_path and os.path.exists(video_path):
                self.analyze_video(video_path)
            else:
                QMessageBox.warning(self, "警告", "视频文件不存在")
        else:
            QMessageBox.warning(self, "警告", "请先选择一个视频")
    
    def on_add_tag(self):
        """添加标签"""
        tag = self.tag_input.text().strip()
        if tag:
            selected_items = self.video_list.selectedItems()
            if selected_items:
                video_info = selected_items[0].data(Qt.UserRole)
                video_id = video_info.get("id")
                
                # 如果是临时视频，提示需要先分析
                if video_id is None:
                    QMessageBox.warning(self, "警告", "请先分析视频后再添加标签！")
                    return
                
                # 添加标签到列表
                self.tag_list.addItem(tag)
                self.tag_input.clear()
                
                # 保存标签到数据库
                current_tags = [self.tag_list.item(i).text() for i in range(self.tag_list.count())]
                original_tags = video_info.get("tags", [])
                
                # 保存到数据库
                conn = sqlite3.connect(self.db_manager.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM video_tags WHERE video_id = ?", (video_id,))
                
                # 添加新标签
                for tag in current_tags:
                    # 确保标签存在
                    cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                    tag_id = cursor.fetchone()[0]
                    cursor.execute("INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)", (video_id, tag_id))
                
                conn.commit()
                conn.close()
                
                # 记录反馈用于自学习
                self.db_manager.add_feedback(video_id, original_tags, current_tags)
                
                # 通知CLIP模型学习
                from models.clip_model import CLIPModel
                clip_model = CLIPModel()
                clip_model.learn_from_feedback(original_tags, current_tags)
                
                # 更新video_info中的tags字段
                video_info["tags"] = current_tags
                
                QMessageBox.information(self, "提示", f"标签 '{tag}' 添加成功")
            else:
                QMessageBox.warning(self, "警告", "请先选择一个视频")
    
    def on_remove_tag(self):
        """删除标签（支持单个和多个标签）"""
        selected_items = self.tag_list.selectedItems()
        if selected_items:
            # 获取视频信息
            video_items = self.video_list.selectedItems()
            if not video_items:
                QMessageBox.warning(self, "警告", "请先选择一个视频")
                return
            
            video_info = video_items[0].data(Qt.UserRole)
            video_id = video_info.get("id")
            
            # 如果是临时视频，提示需要先分析
            if video_id is None:
                QMessageBox.warning(self, "警告", "请先分析视频后再删除标签！")
                return
            
            if len(selected_items) == 1:
                # 单个标签删除
                tag_text = selected_items[0].text()
                reply = QMessageBox.question(
                    self, "确认删除",
                    f"确定要删除标签 '{tag_text}' 吗？",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.tag_list.takeItem(self.tag_list.row(selected_items[0]))
                    
                    # 保存标签到数据库
                    current_tags = [self.tag_list.item(i).text() for i in range(self.tag_list.count())]
                    original_tags = video_info.get("tags", [])
                    
                    # 保存到数据库
                    conn = sqlite3.connect(self.db_manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM video_tags WHERE video_id = ?", (video_id,))
                    
                    # 添加新标签
                    for tag in current_tags:
                        # 确保标签存在
                        cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                        tag_id = cursor.fetchone()[0]
                        cursor.execute("INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)", (video_id, tag_id))
                    
                    conn.commit()
                    conn.close()
                    
                    # 记录反馈用于自学习
                    self.db_manager.add_feedback(video_id, original_tags, current_tags)
                    
                    # 通知CLIP模型学习
                    from models.clip_model import CLIPModel
                    clip_model = CLIPModel()
                    clip_model.learn_from_feedback(original_tags, current_tags)
                    
                    # 更新video_info中的tags字段
                    video_info["tags"] = current_tags
                    
                    QMessageBox.information(self, "提示", f"标签 '{tag_text}' 删除成功")
            else:
                # 多个标签删除
                reply = QMessageBox.question(
                    self, "确认删除",
                    f"确定要删除 {len(selected_items)} 个标签吗？",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    for item in selected_items:
                        self.tag_list.takeItem(self.tag_list.row(item))
                    
                    # 保存标签到数据库
                    current_tags = [self.tag_list.item(i).text() for i in range(self.tag_list.count())]
                    original_tags = video_info.get("tags", [])
                    
                    # 保存到数据库
                    conn = sqlite3.connect(self.db_manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM video_tags WHERE video_id = ?", (video_id,))
                    
                    # 添加新标签
                    for tag in current_tags:
                        # 确保标签存在
                        cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                        tag_id = cursor.fetchone()[0]
                        cursor.execute("INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)", (video_id, tag_id))
                    
                    conn.commit()
                    conn.close()
                    
                    # 记录反馈用于自学习
                    self.db_manager.add_feedback(video_id, original_tags, current_tags)
                    
                    # 通知CLIP模型学习
                    from models.clip_model import CLIPModel
                    clip_model = CLIPModel()
                    clip_model.learn_from_feedback(original_tags, current_tags)
                    
                    # 更新video_info中的tags字段
                    video_info["tags"] = current_tags
                    
                    QMessageBox.information(self, "提示", f"成功删除 {len(selected_items)} 个标签")
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的标签")
    
    def on_rename_video(self):
        """重命名视频"""
        selected_items = self.video_list.selectedItems()
        if selected_items:
            video_info = selected_items[0].data(Qt.UserRole)
            video_path = video_info["path"]
            video_id = video_info["id"]
            
            # 获取当前标签
            current_tags = [self.tag_list.item(i).text() for i in range(self.tag_list.count())]
            if not current_tags:
                QMessageBox.warning(self, "警告", "请先添加标签")
                return
            
            reply = QMessageBox.question(
                self, "确认重命名",
                f"确定要根据标签重命名视频 '{video_info['name']}' 吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    # 调用VideoAnalyzer进行重命名
                    analyzer = VideoAnalyzer(video_path)
                    new_path = analyzer.rename_file(current_tags)
                    
                    # 更新数据库中的路径和名称
                    conn = sqlite3.connect(self.db_manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE videos SET path = ?, name = ? WHERE id = ?",
                        (new_path, os.path.basename(new_path), video_id)
                    )
                    conn.commit()
                    conn.close()
                    
                    QMessageBox.information(self, "重命名成功", "视频重命名成功！")
                    self.load_videos()
                except Exception as e:
                    QMessageBox.warning(self, "重命名失败", f"视频重命名失败: {str(e)}")
        else:
            QMessageBox.warning(self, "警告", "请先选择一个视频")
    
    def on_delete_video(self):
        """删除视频"""
        selected_items = self.video_list.selectedItems()
        if selected_items:
            video_info = selected_items[0].data(Qt.UserRole)
            video_id = video_info["id"]
            
            # 如果是临时视频（未分析），直接从列表移除
            if video_id is None:
                video_path = video_info["path"]
                self.temp_videos = [v for v in self.temp_videos if v["path"] != video_path]
                self.load_videos()
                self.clear_video_details()
                QMessageBox.information(self, "删除成功", "视频已从列表中移除！")
                return
            
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除视频 '{video_info['name']}' 吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.db_manager.delete_video(video_id)
                if success:
                    QMessageBox.information(self, "删除成功", "视频删除成功！")
                    self.load_videos()
                    # 清除右侧内容
                    self.clear_video_details()
                else:
                    QMessageBox.warning(self, "删除失败", "视频删除失败！")
        else:
            QMessageBox.warning(self, "警告", "请先选择一个视频")
    
    def clear_video_details(self):
        """清除视频详情显示"""
        # 清除视频信息
        self.video_info.clear()
        # 清除标签列表
        self.tag_list.clear()
        # 清除缩略图
        self.clear_thumbnails()
        # 清除标签输入框
        self.tag_input.clear()
    
    def on_save_tags(self):
        """保存标签（用于自学习）"""
        selected_items = self.video_list.selectedItems()
        if selected_items:
            video_info = selected_items[0].data(Qt.UserRole)
            video_id = video_info["id"]
            
            # 如果是临时视频，提示需要先分析
            if video_id is None:
                QMessageBox.warning(self, "警告", "请先分析视频后再保存标签！")
                return
            
            # 获取当前标签
            current_tags = [self.tag_list.item(i).text() for i in range(self.tag_list.count())]
            original_tags = video_info.get("tags", [])
            
            # 保存到数据库
            # 这里需要更新数据库中的标签
            # 先删除旧标签关联
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM video_tags WHERE video_id = ?", (video_id,))
            
            # 添加新标签
            for tag in current_tags:
                # 确保标签存在
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                tag_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)", (video_id, tag_id))
            
            conn.commit()
            conn.close()
            
            # 记录反馈用于自学习
            self.db_manager.add_feedback(video_id, original_tags, current_tags)
            
            # 通知CLIP模型学习
            from models.clip_model import CLIPModel
            clip_model = CLIPModel()
            clip_model.learn_from_feedback(original_tags, current_tags)
            
            # 更新video_info中的tags字段
            video_info["tags"] = current_tags
            
            QMessageBox.information(self, "保存成功", "标签保存成功！")
            self.load_videos()
        else:
            QMessageBox.warning(self, "警告", "请先选择一个视频")
    
    def on_context_menu(self, position):
        """视频列表右键菜单"""
        # 获取右键点击的项
        item = self.video_list.itemAt(position)
        if item:
            menu = QMenu()
            
            # 打开视频
            open_action = menu.addAction("打开视频")
            open_action.triggered.connect(self.on_open_video)
            
            # 重命名视频
            rename_action = menu.addAction("重命名视频")
            rename_action.triggered.connect(self.on_rename_video)
            
            # 删除视频
            delete_action = menu.addAction("删除视频")
            delete_action.triggered.connect(self.on_delete_video)
            
            # 显示菜单
            menu.exec_(self.video_list.mapToGlobal(position))
    
    def on_queue_context_menu(self, position):
        """队列列表右键菜单"""
        # 获取右键点击的项
        item = self.queue_list.itemAt(position)
        if item:
            menu = QMenu()
            
            # 获取当前项的索引
            current_index = self.queue_list.row(item)
            
            # 上移
            if current_index > 0:
                move_up_action = menu.addAction("上移")
                move_up_action.triggered.connect(lambda: self.move_queue_item(current_index, current_index - 1))
            
            # 下移
            if current_index < self.queue_list.count() - 1:
                move_down_action = menu.addAction("下移")
                move_down_action.triggered.connect(lambda: self.move_queue_item(current_index, current_index + 1))
            
            # 删除
            delete_action = menu.addAction("删除")
            delete_action.triggered.connect(lambda: self.delete_queue_item(current_index))
            
            # 显示菜单
            menu.exec_(self.queue_list.mapToGlobal(position))
    
    def move_queue_item(self, from_index, to_index):
        """移动队列项
        
        Args:
            from_index: 源索引
            to_index: 目标索引
        """
        # 获取源项
        item = self.queue_list.takeItem(from_index)
        # 插入到目标位置
        self.queue_list.insertItem(to_index, item)
        # 选中移动后的项
        self.queue_list.setCurrentItem(item)
    
    def delete_queue_item(self, index):
        """删除队列项
        
        Args:
            index: 要删除的项的索引
        """
        # 检查是否是当前正在分析的项
        if self.current_queue_item and self.queue_list.row(self.current_queue_item) == index:
            # 如果是当前正在分析的项，先停止分析
            if hasattr(self, 'analysis_thread') and self.analysis_thread and self.analysis_thread.isRunning():
                self.analysis_thread.terminate()
            self.is_analyzing = False
            self.current_queue_item = None
        
        # 删除项
        self.queue_list.takeItem(index)
        
        # 如果删除后队列不为空且当前没有正在分析的视频，则开始分析队列中的第一个视频
        if self.queue_list.count() > 0 and not self.is_analyzing:
            self.process_next_in_queue()
    
    def on_open_video(self):
        """打开视频"""
        selected_items = self.video_list.selectedItems()
        if selected_items:
            video_info = selected_items[0].data(Qt.UserRole)
            video_path = video_info["path"]
            try:
                os.startfile(video_path)
            except Exception as e:
                QMessageBox.warning(self, "打开失败", f"视频打开失败: {str(e)}")
        else:
            QMessageBox.warning(self, "警告", "请先选择一个视频")
    
    def on_search(self):
        """搜索视频"""
        search_text = self.search_input.text().strip()
        if search_text:
            tags = [tag.strip() for tag in search_text.split()]
            videos = self.db_manager.search_videos_by_tags(tags)
            self.video_list.clear()
            for video in videos:
                item = QListWidgetItem(video["name"])
                item.setData(Qt.UserRole, video)
                self.video_list.addItem(item)
        else:
            self.load_videos()
    
    def on_clean_unused_thumbnails(self):
        """清理未使用的缩略图"""
        from utils.thumbnail_cleaner import ThumbnailCleaner
        
        cleaner = ThumbnailCleaner()
        deleted_count = cleaner.clean_unused_thumbnails()
        
        QMessageBox.information(self, "清理完成", f"已清理 {deleted_count} 个未使用的缩略图")
    
    def on_clean_all_thumbnails(self):
        """清理所有缩略图"""
        from utils.thumbnail_cleaner import ThumbnailCleaner
        
        reply = QMessageBox.question(
            self, "确认清理",
            "确定要清理所有缩略图吗？这将删除所有缩略图文件，包括正在使用的。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            cleaner = ThumbnailCleaner()
            deleted_count = cleaner.clean_all_thumbnails()
            QMessageBox.information(self, "清理完成", f"已清理 {deleted_count} 个缩略图")
    
    def show_model_train_page(self):
        """显示模型训练页面"""
        if self.model_train_page is None:
            self.model_train_page = ModelTrainPage(self)
        self.model_train_page.show()

class ModelTrainPage(QMainWindow):
    """模型训练页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模型训练")
        self.setGeometry(100, 100, 1000, 800)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 视频文件选择（放到最上面）
        video_select_layout = QHBoxLayout()
        video_select_layout.addWidget(QLabel("视频文件:"))
        self.video_file_input = QLineEdit()
        self.video_file_input.setPlaceholderText("选择视频文件")
        video_select_layout.addWidget(self.video_file_input)
        video_select_button = QPushButton("浏览")
        video_select_button.clicked.connect(self.on_select_video_file)
        video_select_layout.addWidget(video_select_button)
        main_layout.addLayout(video_select_layout)
        
        # 输出目录选择
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(QLabel("输出目录:"))
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText("custom_model")
        output_dir_layout.addWidget(self.output_dir_input)
        output_dir_button = QPushButton("浏览")
        output_dir_button.clicked.connect(self.on_select_output_dir)
        output_dir_layout.addWidget(output_dir_button)
        main_layout.addLayout(output_dir_layout)
        
        # 运行步骤按钮
        step_buttons_layout = QHBoxLayout()
        step_buttons_layout.addWidget(QLabel("运行步骤:"))
        
        self.build_dataset_button = QPushButton("构建数据集")
        self.build_dataset_button.clicked.connect(lambda: self.on_run_step("构建数据集"))
        step_buttons_layout.addWidget(self.build_dataset_button)
        
        self.annotate_button = QPushButton("半自动标注")
        self.annotate_button.clicked.connect(lambda: self.on_run_step("半自动标注"))
        step_buttons_layout.addWidget(self.annotate_button)
        
        self.train_button = QPushButton("训练模型")
        self.train_button.clicked.connect(lambda: self.on_run_step("训练模型"))
        step_buttons_layout.addWidget(self.train_button)
        
        main_layout.addLayout(step_buttons_layout)
        
        # 参数设置
        params_layout = QGridLayout()
        
        # 提取帧数量
        params_layout.addWidget(QLabel("每个视频提取帧数量:"), 0, 0)
        self.num_frames_input = QLineEdit()
        self.num_frames_input.setText("30")
        params_layout.addWidget(self.num_frames_input, 0, 1)
        
        # 训练集比例
        params_layout.addWidget(QLabel("训练集比例:"), 1, 0)
        self.train_ratio_input = QLineEdit()
        self.train_ratio_input.setText("0.7")
        params_layout.addWidget(self.train_ratio_input, 1, 1)
        
        # 验证集比例
        params_layout.addWidget(QLabel("验证集比例:"), 2, 0)
        self.val_ratio_input = QLineEdit()
        self.val_ratio_input.setText("0.15")
        params_layout.addWidget(self.val_ratio_input, 2, 1)
        
        # 置信度阈值
        params_layout.addWidget(QLabel("置信度阈值:"), 3, 0)
        self.confidence_threshold_input = QLineEdit()
        self.confidence_threshold_input.setText("0.5")
        params_layout.addWidget(self.confidence_threshold_input, 3, 1)
        
        # 训练轮数
        params_layout.addWidget(QLabel("训练轮数:"), 4, 0)
        self.epochs_input = QLineEdit()
        self.epochs_input.setText("50")
        params_layout.addWidget(self.epochs_input, 4, 1)
        
        # 批处理大小
        params_layout.addWidget(QLabel("批处理大小:"), 5, 0)
        self.batch_size_input = QLineEdit()
        self.batch_size_input.setText("32")
        params_layout.addWidget(self.batch_size_input, 5, 1)
        
        # 学习率
        params_layout.addWidget(QLabel("学习率:"), 6, 0)
        self.lr_input = QLineEdit()
        self.lr_input.setText("0.0001")
        params_layout.addWidget(self.lr_input, 6, 1)
        
        main_layout.addLayout(params_layout)
        
        # 日志输出
        log_layout = QVBoxLayout()
        log_layout.addWidget(QLabel("运行日志:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        main_layout.addLayout(log_layout)
    
    def on_select_video_dir(self):
        """选择视频目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择视频目录")
        if dir_path:
            self.video_dir_input.setText(dir_path)
    
    def on_select_output_dir(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_input.setText(dir_path)
    
    def on_select_video_file(self):
        """选择视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.webm)"
        )
        if file_path:
            self.video_file_input.setText(file_path)
    
    def on_run_step(self, step):
        """运行指定步骤"""
        # 获取参数
        video_file = self.video_file_input.text()
        output_dir = self.output_dir_input.text()
        
        # 检查输入
        if step == "构建数据集":
            if not video_file:
                QMessageBox.warning(self, "警告", "请选择视频文件")
                return
        else:
            if not output_dir:
                QMessageBox.warning(self, "警告", "请设置输出目录")
                return
        
        try:
            num_frames = int(self.num_frames_input.text())
            train_ratio = float(self.train_ratio_input.text())
            val_ratio = float(self.val_ratio_input.text())
            confidence_threshold = float(self.confidence_threshold_input.text())
            epochs = int(self.epochs_input.text())
            batch_size = int(self.batch_size_input.text())
            lr = float(self.lr_input.text())
        except ValueError:
            QMessageBox.warning(self, "警告", "请输入有效的参数")
            return
        
        # 运行训练
        self.log_text.clear()
        self.log_text.append(f"开始运行: {step}")
        
        try:
            from train_custom_model import TrainCustomModel
            
            # 使用视频文件
            trainer = TrainCustomModel(video_file, output_dir)
            
            if step == "构建数据集":
                self.log_text.append("=== 构建数据集 ===")
                trainer.build_dataset(num_frames, train_ratio, val_ratio)
            elif step == "半自动标注":
                self.log_text.append("=== 半自动标注 ===")
                trainer.annotate_dataset(confidence_threshold)
            elif step == "训练模型":
                self.log_text.append("=== 模型训练 ===")
                trainer.train_model(epochs, batch_size, lr)
            
            self.log_text.append("运行完成！")
            QMessageBox.information(self, "提示", "运行完成！")
        except Exception as e:
            self.log_text.append(f"运行失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"运行失败: {str(e)}")
