#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
翻译工具模块
"""

import os
from typing import List, Optional

try:
    import argostranslate.package
    import argostranslate.translate
    HAS_ARGOS = True
except ImportError:
    HAS_ARGOS = False

class Translator:
    """翻译工具类"""
    
    def __init__(self):
        """初始化翻译工具"""
        self.has_translation = HAS_ARGOS
        self._ensure_translation_models()
    
    def _ensure_translation_models(self):
        """确保翻译模型已安装"""
        if not HAS_ARGOS:
            print("警告: argos-translate 库未安装，翻译功能将不可用")
            return
        
        try:
            # 检查中译英模型是否已安装
            available_languages = argostranslate.translate.get_available_languages()
            zh_en_available = any(
                lang.code == "zh" and "en" in [t.code for t in lang.translations]
                for lang in available_languages
            )
            
            if not zh_en_available:
                print("正在下载中译英翻译模型...")
                argostranslate.package.update_package_index()
                available_packages = argostranslate.package.get_available_packages()
                package_to_install = next(
                    filter(
                        lambda x: x.from_code == "zh" and x.to_code == "en",
                        available_packages
                    ),
                    None
                )
                if package_to_install:
                    argostranslate.package.install_from_path(package_to_install.download())
                    print("中译英翻译模型安装成功")
                else:
                    print("警告: 无法找到中译英翻译模型")
                    self.has_translation = False
        except Exception as e:
            print(f"初始化翻译模型失败: {e}")
            self.has_translation = False
    
    def translate(self, text: str, target_language: str = "en") -> Optional[str]:
        """翻译文本
        
        Args:
            text: 要翻译的文本
            target_language: 目标语言代码，默认为英文 (en)
            
        Returns:
            翻译后的文本，如果翻译失败则返回None
        """
        if not self.has_translation or not text:
            return None
        
        try:
            translated_text = argostranslate.translate.translate(text, "zh", target_language)
            return translated_text
        except Exception as e:
            print(f"翻译失败: {e}")
            return None
    
    def translate_tags(self, tags: List[str], target_language: str = "en") -> List[str]:
        """翻译标签列表
        
        Args:
            tags: 要翻译的标签列表
            target_language: 目标语言代码，默认为英文 (en)
            
        Returns:
            翻译后的标签列表
        """
        if not self.has_translation:
            return tags
        
        translated_tags = []
        for tag in tags:
            translated = self.translate(tag, target_language)
            if translated:
                # 清理翻译结果，移除多余的空格，转换为小写
                translated = translated.strip().lower()
                # 替换空格为下划线
                translated = translated.replace(" ", "_")
                translated_tags.append(translated)
            else:
                translated_tags.append(tag)
        
        return translated_tags
    
    def is_available(self) -> bool:
        """检查翻译功能是否可用
        
        Returns:
            翻译功能是否可用
        """
        return self.has_translation
