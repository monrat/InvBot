"""
发票信息提取模块
负责调用Qwen模型进行OCR识别和Excel数据写入
"""
import json
import logging
import os
import threading
import pandas as pd
from datetime import datetime
from pathlib import Path
from PIL import Image
from typing import Dict, Any, Optional

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from qwen_vl_utils import process_vision_info
except ImportError as e:
    logging.error(f"导入模型相关库失败: {e}")
    logging.error("请确保已安装 transformers 和 qwen-vl-utils")


class InvoiceExtractor:
    """发票信息提取器"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.excel_lock = threading.Lock()
        
        # 初始化模型和分词器
        self.model = None
        self.tokenizer = None
        self._init_model()
    
    def _init_model(self):
        """初始化Qwen模型"""
        try:
            if not os.path.exists(self.config.model_path):
                self.logger.error(f"模型路径不存在: {self.config.model_path}")
                self.logger.info("请下载Qwen2.5-VL-3B-Instruct模型到指定目录")
                return
            
            self.logger.info("正在加载Qwen模型...")
            
            # 加载分词器
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_path, 
                trust_remote_code=True
            )
            
            # 加载模型
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_path,
                device_map="auto",
                trust_remote_code=True
            ).eval()
            
            self.logger.info("Qwen模型加载成功")
            
        except Exception as e:
            self.logger.error(f"模型初始化失败: {e}")
            self.model = None
            self.tokenizer = None
    
    def extract_invoice_info(self, image_path: str) -> Optional[Dict[str, Any]]:
        """从图片中提取发票信息"""
        if self.model is None or self.tokenizer is None:
            self.logger.error("模型未初始化，无法进行提取")
            return None
        
        try:
            self.logger.info(f"开始处理图片: {image_path}")
            
            # 准备输入
            image = Image.open(image_path)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": self.config.model_prompt}
                    ]
                }
            ]
            
            # 处理多模态输入
            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            image_inputs, video_inputs = process_vision_info(messages)
            
            inputs = self.tokenizer(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            )
            inputs = inputs.to(self.model.device)
            
            # 生成回复
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                temperature=0.1
            )
            
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in 
                zip(inputs.input_ids, generated_ids)
            ]
            
            output_text = self.tokenizer.batch_decode(
                generated_ids_trimmed, 
                skip_special_tokens=True, 
                clean_up_tokenization_spaces=False
            )[0]
            
            self.logger.info(f"模型输出: {output_text}")
            
            # 解析JSON
            json_data = self._parse_json_from_text(output_text)
            if json_data:
                # 添加元数据
                json_data['image_path'] = image_path
                json_data['extracted_time'] = datetime.now().isoformat()
                return json_data
            else:
                self.logger.error("无法从模型输出中解析JSON")
                return None
                
        except Exception as e:
            self.logger.error(f"提取发票信息时出错: {e}")
            return None
    
    def _parse_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """从文本中解析JSON"""
        try:
            # 尝试找到JSON部分
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_str = text[start_idx:end_idx + 1]
                return json.loads(json_str)
            else:
                # 如果没有找到花括号，尝试整个文本
                return json.loads(text.strip())
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误: {e}")
            self.logger.error(f"原始文本: {text}")
            return None
    
    def save_to_excel(self, data: Dict[str, Any]) -> bool:
        """保存数据到Excel文件"""
        try:
            with self.excel_lock:
                # 创建DataFrame
                df = pd.DataFrame([data])
                
                # 检查Excel文件是否存在
                excel_path = Path(self.config.excel_file)
                
                if excel_path.exists():
                    # 文件存在，追加数据
                    with pd.ExcelWriter(
                        str(excel_path), 
                        mode='a', 
                        engine='openpyxl',
                        if_sheet_exists='overlay'
                    ) as writer:
                        # 读取现有数据以确定起始行
                        try:
                            existing_df = pd.read_excel(str(excel_path))
                            start_row = len(existing_df) + 1
                        except:
                            start_row = 1
                        
                        df.to_excel(
                            writer, 
                            index=False, 
                            header=(start_row == 1),
                            startrow=start_row
                        )
                else:
                    # 文件不存在，创建新文件
                    df.to_excel(str(excel_path), index=False)
                
                self.logger.info(f"数据已保存到 {excel_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"保存Excel时出错: {e}")
            return False
    
    def process_image(self, image_path: str) -> bool:
        """处理单张图片（提取信息并保存）"""
        try:
            # 提取发票信息
            invoice_data = self.extract_invoice_info(image_path)
            if invoice_data is None:
                return False
            
            # 保存到Excel
            success = self.save_to_excel(invoice_data)
            
            if success:
                self.logger.info(f"图片处理完成: {image_path}")
                # 可选：删除已处理的图片以节省空间
                # os.remove(image_path)
            
            return success
            
        except Exception as e:
            self.logger.error(f"处理图片时出错 {image_path}: {e}")
            return False
    
    def get_model_status(self) -> Dict[str, Any]:
        """获取模型状态"""
        return {
            "model_loaded": self.model is not None,
            "tokenizer_loaded": self.tokenizer is not None,
            "model_path": self.config.model_path
        } 