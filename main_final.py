#!/usr/bin/env python3
"""
财务单据自动抓拍识别工具 v1.0 RC
主程序入口文件

功能：
- 通过高拍仪/俯拍相机自动检测票据出现
- 高清抓拍并调用Qwen2.5-VL模型抽取关键字段
- 输出JSON并追加写入Excel

作者：AI4FIN Team
版本：1.0 RC
"""

import logging
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 导入自定义模块
try:
    from app.config import Config
    from app.camera import CameraWatcher
    from app.extractor import InvoiceExtractor
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保app目录下的模块存在")
    sys.exit(1)


class InvoiceBot:
    """财务单据自动识别机器人"""
    
    def __init__(self, config_path: str = "config.json"):
        # 加载配置
        try:
            self.config = Config(config_path)
        except Exception as e:
            print(f"配置文件加载失败: {e}")
            sys.exit(1)
        
        # 设置日志
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.exit_event = threading.Event()
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        # 初始化模块
        self.camera_watcher = CameraWatcher(self.config, self.exit_event)
        self.invoice_extractor = InvoiceExtractor(self.config)
        
        # 统计信息
        self.stats = {
            "total_captures": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "start_time": time.time()
        }
        
        self.logger.info("财务单据自动识别工具启动")
        self.logger.info(f"配置文件: {config_path}")
        self.logger.info(f"输出目录: {self.config.shots_dir}")
        self.logger.info(f"结果文件: {self.config.excel_file}")
    
    def _setup_logging(self):
        """设置日志系统"""
        from logging.handlers import RotatingFileHandler
        
        # 创建logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # 清除现有的handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 文件处理器（轮转日志）
        file_handler = RotatingFileHandler(
            self.config.log_file,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    def _on_image_captured(self, image_path: str):
        """当抓拍到图片时的回调函数"""
        try:
            self.stats["total_captures"] += 1
            self.logger.info(f"接收到新抓拍图片: {image_path}")
            
            # 提交任务到线程池
            self.thread_pool.submit(self._process_image_task, image_path)
            self.logger.debug(f"图片处理任务已提交: {image_path}")
                
        except Exception as e:
            self.logger.error(f"处理抓拍回调时出错: {e}")
    
    def _process_image_task(self, image_path: str):
        """处理图片的任务函数"""
        try:
            self.logger.info(f"开始处理图片: {image_path}")
            
            # 调用提取器处理图片
            success = self.invoice_extractor.process_image(image_path)
            
            if success:
                self.stats["successful_extractions"] += 1
                self.logger.info(f"图片处理成功: {image_path}")
            else:
                self.stats["failed_extractions"] += 1
                self.logger.error(f"图片处理失败: {image_path}")
            
            # 打印统计信息
            self._print_stats()
            
        except Exception as e:
            self.stats["failed_extractions"] += 1
            self.logger.error(f"处理图片任务时出错 {image_path}: {e}")
    
    def _print_stats(self):
        """打印统计信息"""
        runtime = time.time() - self.stats["start_time"]
        self.logger.info(
            f"统计信息 - 总抓拍: {self.stats['total_captures']}, "
            f"成功: {self.stats['successful_extractions']}, "
            f"失败: {self.stats['failed_extractions']}, "
            f"运行时间: {runtime:.1f}秒"
        )
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"接收到信号 {signum}，准备退出...")
            self.exit_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """启动系统"""
        try:
            self.logger.info("="*50)
            self.logger.info("财务单据自动识别工具启动")
            self.logger.info("="*50)
            
            # 检查模型状态
            model_status = self.invoice_extractor.get_model_status()
            if not model_status["model_loaded"]:
                self.logger.error("Qwen模型未正确加载，请检查模型路径和依赖")
                return
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            # 启动摄像头监控（主线程）
            self.logger.info("开始摄像头监控...")
            self.camera_watcher.start_monitoring(self._on_image_captured)
            
        except KeyboardInterrupt:
            self.logger.info("接收到键盘中断信号")
        except Exception as e:
            self.logger.error(f"启动时出错: {e}")
        finally:
            self._shutdown()
    
    def _shutdown(self):
        """优雅关闭系统"""
        self.logger.info("开始关闭系统...")
        
        # 设置退出事件
        self.exit_event.set()
        
        # 等待线程池中的任务完成
        self.logger.info("等待处理任务完成...")
        try:
            # 等待所有任务完成并关闭线程池
            self.thread_pool.shutdown(wait=True)
            self.logger.info("所有处理任务已完成")
        except Exception as e:
            self.logger.error(f"关闭线程池时出错: {e}")
        
        # 打印最终统计
        self._print_stats()
        
        self.logger.info("="*50)
        self.logger.info("财务单据自动识别工具已关闭")
        self.logger.info("="*50)


def print_welcome():
    """打印欢迎信息"""
    print("="*60)
    print("        财务单据自动抓拍识别工具 v1.0 RC")
    print("="*60)
    print("功能：")
    print("  • 自动检测票据出现并抓拍")
    print("  • 使用Qwen2.5-VL模型提取关键信息")
    print("  • 自动保存结果到Excel文件")
    print()
    print("操作说明：")
    print("  • 按 ESC 键（在摄像头窗口）或 Ctrl+C 退出")
    print("  • 将票据放在摄像头视野内即可自动识别")
    print("="*60)
    print()


def check_environment():
    """检查运行环境"""
    issues = []
    
    # 检查配置文件
    if not Path("config.json").exists():
        issues.append("配置文件 config.json 不存在")
    
    # 检查必要的目录
    required_dirs = ["models", "shots"]
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            Path(dir_name).mkdir(exist_ok=True)
            print(f"已创建目录: {dir_name}")
    
    # 检查模型目录
    model_path = Path("models/qwen-3b")
    if not model_path.exists():
        issues.append(f"模型目录不存在: {model_path}")
        issues.append("请下载Qwen2.5-VL-3B-Instruct模型到 models/qwen-3b 目录")
    
    return issues


def main():
    """主函数"""
    print_welcome()
    
    # 检查环境
    issues = check_environment()
    if issues:
        print("环境检查发现问题：")
        for issue in issues:
            print(f"  ❌ {issue}")
        print("\n请解决以上问题后重新运行程序")
        return
    
    try:
        # 创建并启动机器人
        bot = InvoiceBot()
        bot.start()
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        logging.error(f"程序启动失败: {e}")


if __name__ == "__main__":
    main()
