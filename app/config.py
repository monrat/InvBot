"""
配置管理模块
负责读取和校验config.json配置文件
"""
import json
import os
from typing import Dict, Any


class Config:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件未找到: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def _validate_config(self):
        """验证配置文件的必要字段"""
        required_sections = ['camera', 'detection', 'processing', 'model', 'output']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"配置文件缺少必要部分: {section}")
        
        # 验证摄像头配置
        camera_config = self.config['camera']
        if 'device_id' not in camera_config:
            raise ValueError("摄像头配置缺少device_id")
        
        # 验证模型配置
        model_config = self.config['model']
        if 'path' not in model_config or 'prompt' not in model_config:
            raise ValueError("模型配置缺少path或prompt")
    
    def get(self, section: str, key: str = None):
        """获取配置值"""
        if key is None:
            return self.config.get(section, {})
        return self.config.get(section, {}).get(key)
    
    @property
    def camera_device_id(self) -> int:
        return self.get('camera', 'device_id')
    
    @property
    def high_res(self) -> tuple:
        return tuple(self.get('camera', 'high_res'))
    
    @property
    def detect_res(self) -> tuple:
        return tuple(self.get('camera', 'detect_res'))
    
    @property
    def motion_threshold(self) -> int:
        return self.get('detection', 'motion_threshold')
    
    @property
    def stable_frames_trigger(self) -> int:
        return self.get('detection', 'stable_frames_trigger')
    
    @property
    def capture_interval_sec(self) -> float:
        return self.get('detection', 'capture_interval_sec')
    
    @property
    def max_workers(self) -> int:
        return self.get('processing', 'max_workers')
    
    @property
    def model_path(self) -> str:
        return self.get('model', 'path')
    
    @property
    def model_prompt(self) -> str:
        return self.get('model', 'prompt')
    
    @property
    def shots_dir(self) -> str:
        return self.get('output', 'shots_dir')
    
    @property
    def excel_file(self) -> str:
        return self.get('output', 'excel_file')
    
    @property
    def log_file(self) -> str:
        return self.get('output', 'log_file') 