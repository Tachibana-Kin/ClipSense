# ClipSense

VidTagger – Automatic video content understanding and tagging using multimodal AI (vision, audio, and text).

基于AI的视频分析与管理工具，支持视频内容识别、标签管理、缩略图生成等功能。

## 功能特性

- **视频分析**：自动分析视频内容，提取关键帧
- **AI识别**：
  - CLIP视觉理解（场景、物体识别）
  - Whisper语音识别（语音转文字）
  - EasyOCR文字识别（画面文字提取）
  - 服饰识别（服装类型检测）
- **标签管理**：
  - 自动标签融合
  - 手动编辑标签
  - 标签增删改查
  - 基于用户反馈的自学习
- **缩略图生成**：自动生成视频缩略图
- **文件管理**：支持视频重命名、删除
- **数据库**：SQLite存储视频信息和分析结果
- **GUI界面**：PyQt5图形界面，支持搜索和浏览

## 工作流程

```
视频 → 抽帧 → CLIP视觉理解 → Whisper语音 → OCR文字 → 服饰识别 → 标签融合（可编辑）→ 缩略图生成 → 写入数据库 → GUI展示+搜索
```

## 安装说明

### 环境要求

- Python 3.8+
- Windows/Linux/macOS

### 安装步骤

1. 克隆仓库
```bash
git clone <repository-url>
cd Video_Collector
```

2. 创建虚拟环境（推荐）
```bash
python -m venv venv
```

3. 激活虚拟环境
- Windows:
```bash
venv\Scripts\activate
```
- Linux/macOS:
```bash
source venv/bin/activate
```

4. 安装依赖
```bash
pip install -r requirements.txt
```

### 快速启动

Windows用户可以直接运行：
```bash
start.bat
```

或手动运行：
```bash
python main.py
```

## 使用指南

### 1. 添加视频

- 点击"添加视频"按钮选择视频文件
- 系统自动分析视频内容

### 2. 查看分析结果

- 在左侧列表选择视频
- 右侧显示视频信息、标签、缩略图

### 3. 编辑标签

- 在标签输入框输入新标签
- 点击"添加标签"或"删除标签"
- 点击"保存标签"保存修改并训练模型

### 4. 搜索视频

- 在搜索框输入标签关键词
- 支持多标签搜索（空格分隔）

### 5. 右键菜单操作

在视频列表上右键可：
- **打开视频**：使用系统默认播放器
- **重命名视频**：根据标签重命名文件
- **删除视频**：删除数据库记录（不清除文件）

### 6. 自学习功能

- 修改视频标签后点击"保存标签"
- 系统会记录反馈并调整标签权重
- 随着使用次数增加，识别准确率会提升

## 项目结构

```
Video_Collector/
├── main.py                     # 程序入口
├── start.bat                   # Windows启动脚本
├── requirements.txt            # 依赖配置
├── README.md                   # 项目说明
├── .gitignore                  # Git忽略配置
│
├── models/                     # AI模型
│   ├── clip_model.py          # CLIP视觉模型
│   ├── whisper_model.py       # Whisper语音模型
│   ├── ocr_model.py           # EasyOCR文字识别
│   └── clothes_model.py       # 服饰识别模型
│
├── video_processor/            # 视频处理
│   └── video_analyzer.py      # 视频分析器
│
├── utils/                      # 工具模块
│   ├── tag_manager.py         # 标签管理
│   ├── thumbnail_generator.py # 缩略图生成
│   └── file_renamer.py        # 文件重命名
│
├── database/                   # 数据库
│   └── db_manager.py          # 数据库管理
│
└── gui/                        # 图形界面
    └── main_window.py         # 主窗口
```

## 技术栈

- **GUI**: PyQt5
- **视频处理**: OpenCV, MoviePy
- **AI模型**:
  - CLIP (OpenAI) - 视觉理解
  - Whisper (OpenAI) - 语音识别
  - EasyOCR - 文字识别
- **数据库**: SQLite
- **深度学习**: PyTorch

## 模型说明

### CLIP模型
- 自动下载预训练权重
- 支持中英文标签
- 具有自学习能力

### Whisper模型
- 首次使用自动下载模型
- 支持中文语音识别
- 可选模型大小: tiny, base, small, medium, large

### EasyOCR模型
- 首次使用自动下载语言包
- 支持中英文混合识别
- 支持GPU加速（如有）

## 注意事项

1. **首次运行**：首次使用AI模型时会自动下载权重文件，需要网络连接
2. **存储空间**：AI模型权重文件较大（约1-3GB），请确保有足够空间
3. **性能**：视频分析需要一定时间，取决于视频长度和硬件性能
4. **GPU加速**：如有NVIDIA显卡并安装CUDA，可显著提升分析速度

## 自学习能力

系统通过以下方式学习：
1. 记录用户对标签的修改
2. 调整标签权重
3. 优化后续识别结果

反馈数据保存在 `feedback.json` 文件中。

## 数据库

SQLite数据库文件 `video_manager.db` 包含以下表：
- **videos**: 视频基本信息
- **tags**: 标签列表
- **video_tags**: 视频-标签关联
- **video_metadata**: 视频分析元数据
- **feedback**: 用户反馈记录

## 开发计划

- [x] 基础视频分析功能
- [x] CLIP视觉识别
- [x] Whisper语音识别
- [x] OCR文字识别
- [x] 标签管理与融合
- [x] 缩略图生成
- [x] 数据库管理
- [x] GUI界面
- [x] 搜索功能
- [x] 自学习能力
- [x] 右键菜单操作
- [ ] 批量处理
- [ ] 视频预览播放
- [ ] 标签统计报表
- [ ] 导出功能

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题或建议，请通过GitHub Issues联系。

## 更新日志

- 2026-03-29: 初始版本发布
