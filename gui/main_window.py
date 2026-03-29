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
    QMessageBox, QProgressBar, QMenu
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from video_processor.video_analyzer import VideoAnalyzer
from database.db_manager import DBManager

class AnalysisThread(QThread):
    """分析线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict, list)
    error = pyqtSignal(str)
    
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
    
    def run(self):
        try:
            analyzer = VideoAnalyzer(self.video_path)
            
            # 分析视频
            self.progress.emit(20)
            analysis_result = analyzer.analyze_video()
            
            # 生成缩略图（使用已提取的帧）
            self.progress.emit(60)
            # 使用默认的工程目录下的thumbnails文件夹
            frames = analysis_result.get("frames", [])
            thumbnail_paths = analyzer.generate_thumbnails(frames=frames)
            
            # 保存到数据库
            self.progress.emit(90)
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
        save_tags_button = QPushButton("保存标签")
        save_tags_button.clicked.connect(self.on_save_tags)
        top_buttons.addWidget(add_button)
        top_buttons.addWidget(analyze_button)
        top_buttons.addWidget(save_tags_button)
        right_layout.addLayout(top_buttons)
        
        # 为视频列表添加右键菜单
        self.video_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.video_list.customContextMenuRequested.connect(self.on_context_menu)
        
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
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
    
    def load_videos(self):
        """加载视频列表"""
        self.video_list.clear()
        videos = self.db_manager.get_all_videos()
        for video in videos:
            item = QListWidgetItem(video["name"])
            item.setData(Qt.UserRole, video)
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
                        # 调整缩略图大小
                        pixmap = pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        label = QLabel()
                        label.setPixmap(pixmap)
                        label.setFixedSize(300, 200)
                        # 一行显示3张
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
            item = QListWidgetItem(video_name)
            item.setData(Qt.UserRole, video_info)
            self.video_list.addItem(item)
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
                # 清空当前列表
                self.video_list.clear()
                
                # 添加视频文件到列表
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
                    item = QListWidgetItem(video_name)
                    item.setData(Qt.UserRole, video_info)
                    self.video_list.addItem(item)
                
                QMessageBox.information(self, "导入成功", f"成功导入 {len(video_files)} 个视频文件")
            else:
                QMessageBox.warning(self, "未找到视频", "所选文件夹中没有找到视频文件")
    
    def analyze_video(self, video_path):
        """分析视频"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.analysis_thread = AnalysisThread(video_path)
        self.analysis_thread.progress.connect(self.on_progress)
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.start()
    
    def on_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)
    
    def on_analysis_finished(self, analysis_result, thumbnail_paths):
        """分析完成"""
        self.progress_bar.setValue(100)
        QMessageBox.information(self, "分析完成", "视频分析完成！")
        self.progress_bar.setVisible(False)
        # 重新加载当前选中的视频信息
        selected_items = self.video_list.selectedItems()
        if selected_items:
            video_name = selected_items[0].text()
            # 重新加载视频列表
            self.load_videos()
            # 重新选择原来的视频
            for i in range(self.video_list.count()):
                item = self.video_list.item(i)
                if item.text() == video_name:
                    self.video_list.setCurrentItem(item)
                    break
    
    def on_analysis_error(self, error):
        """分析错误"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "分析错误", f"分析失败: {error}")
    
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
                # 这里需要实现标签添加逻辑
                QMessageBox.information(self, "提示", f"标签 '{tag}' 添加成功")
                self.tag_list.addItem(tag)
                self.tag_input.clear()
            else:
                QMessageBox.warning(self, "警告", "请先选择一个视频")
    
    def on_remove_tag(self):
        """删除标签（支持单个和多个标签）"""
        selected_items = self.tag_list.selectedItems()
        if selected_items:
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