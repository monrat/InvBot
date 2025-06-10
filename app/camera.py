"""
摄像头监控模块
负责视频流读取、运动检测和抓拍功能
"""
import cv2
import os
import logging
import time
from pathlib import Path
from threading import Event
from typing import Optional, Callable


class CameraWatcher:
    """摄像头监控器"""
    
    def __init__(self, config, exit_event: Event):
        self.config = config
        self.exit_event = exit_event
        self.logger = logging.getLogger(__name__)
        
        # 初始化摄像头
        self.cap = None
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2()
        
        # 状态变量
        self.stable_count = 0
        self.last_capture_time = 0
        self.frame_count = 0
        
        # 确保输出目录存在
        Path(self.config.shots_dir).mkdir(exist_ok=True)
    
    def _init_camera(self) -> bool:
        """初始化摄像头"""
        try:
            if self.cap is not None:
                self.cap.release()
            
            self.cap = cv2.VideoCapture(self.config.camera_device_id)
            if not self.cap.isOpened():
                self.logger.error(f"无法打开摄像头 {self.config.camera_device_id}")
                return False
            
            # 设置高分辨率
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.high_res[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.high_res[1])
            
            self.logger.info(f"摄像头初始化成功，分辨率: {self.config.high_res}")
            return True
            
        except Exception as e:
            self.logger.error(f"摄像头初始化失败: {e}")
            return False
    
    def _detect_motion(self, frame) -> bool:
        """检测运动"""
        try:
            # 缩放到低分辨率进行检测
            frame_small = cv2.resize(frame, self.config.detect_res)
            
            # 背景差分
            fg_mask = self.bg_subtractor.apply(frame_small)
            moving_pixels = cv2.countNonZero(fg_mask)
            
            # 判断是否静止
            is_stable = moving_pixels < self.config.motion_threshold
            
            if is_stable:
                self.stable_count += 1
            else:
                self.stable_count = 0
            
            return self.stable_count >= self.config.stable_frames_trigger
            
        except Exception as e:
            self.logger.error(f"运动检测错误: {e}")
            return False
    
    def _capture_frame(self, frame) -> Optional[str]:
        """抓拍帧并保存"""
        try:
            # 检查抓拍间隔
            current_time = time.time()
            if current_time - self.last_capture_time < self.config.capture_interval_sec:
                return None
            
            # 生成文件名
            timestamp = int(current_time * 1000)
            filename = Path(self.config.shots_dir) / f"shot_{timestamp}.jpg"
            
            # 保存高清图片
            success = cv2.imwrite(str(filename), frame)
            if success:
                self.last_capture_time = current_time
                self.stable_count = 0  # 重置稳定计数
                self.logger.info(f"抓拍成功: {filename}")
                return str(filename)
            else:
                self.logger.error("保存图片失败")
                return None
                
        except Exception as e:
            self.logger.error(f"抓拍错误: {e}")
            return None
    
    def start_monitoring(self, on_capture: Callable[[str], None]):
        """开始监控"""
        self.logger.info("开始摄像头监控...")
        
        # 初始化摄像头
        if not self._init_camera():
            return
        
        failed_frames = 0
        max_failed_frames = 30  # 连续失败30帧后重连
        
        try:
            while not self.exit_event.is_set():
                ret, frame = self.cap.read()
                
                if not ret:
                    failed_frames += 1
                    self.logger.warning(f"读取帧失败 ({failed_frames}/{max_failed_frames})")
                    
                    if failed_frames >= max_failed_frames:
                        self.logger.error("连续读帧失败，尝试重连摄像头...")
                        if self._init_camera():
                            failed_frames = 0
                        else:
                            break
                    continue
                
                failed_frames = 0
                self.frame_count += 1
                
                # 显示预览窗口（可选）
                cv2.imshow('Invoice Scanner', cv2.resize(frame, (640, 480)))
                
                # 检测ESC键退出
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC键
                    self.logger.info("用户按ESC键退出")
                    self.exit_event.set()
                    break
                
                # 运动检测
                if self._detect_motion(frame):
                    # 检测到稳定状态，进行抓拍
                    captured_file = self._capture_frame(frame)
                    if captured_file:
                        # 异步处理抓拍的图片
                        on_capture(captured_file)
                
        except KeyboardInterrupt:
            self.logger.info("接收到中断信号")
            self.exit_event.set()
        except Exception as e:
            self.logger.error(f"监控循环错误: {e}")
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()
            self.logger.info("摄像头资源清理完成")
        except Exception as e:
            self.logger.error(f"清理资源时出错: {e}")
    
    def get_status(self) -> dict:
        """获取监控状态"""
        return {
            "frame_count": self.frame_count,
            "stable_count": self.stable_count,
            "last_capture_time": self.last_capture_time,
            "is_camera_opened": self.cap.isOpened() if self.cap else False
        } 