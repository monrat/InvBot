#!/usr/bin/env python3
"""
环境测试脚本
验证依赖安装和硬件配置是否正确
"""

import sys
import os
from pathlib import Path

def test_python_version():
    """测试Python版本"""
    print("🐍 Python版本检查:")
    version = sys.version_info
    print(f"  当前版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 10:
        print("  ✅ Python版本符合要求 (>=3.10)")
        return True
    else:
        print("  ❌ Python版本过低，需要3.10及以上版本")
        return False

def test_dependencies():
    """测试依赖包"""
    print("\n📦 依赖包检查:")
    
    required_packages = [
        ("opencv-python", "cv2"),
        ("pillow", "PIL"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("torch", "torch"),
        ("transformers", "transformers")
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} - 未安装")
            missing_packages.append(package_name)
    
    # 检查特殊包
    try:
        import qwen_vl_utils
        print(f"  ✅ qwen-vl-utils")
    except ImportError:
        print(f"  ❌ qwen-vl-utils - 未安装")
        missing_packages.append("qwen-vl-utils")
    
    return len(missing_packages) == 0, missing_packages

def test_gpu():
    """测试GPU配置"""
    print("\n🎮 GPU配置检查:")
    
    try:
        import torch
        if torch.cuda.is_available():
            print("  ✅ CUDA可用")
            print(f"  GPU数量: {torch.cuda.device_count()}")
            
            for i in range(torch.cuda.device_count()):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1024**3
                print(f"  GPU {i}: {gpu_name} ({gpu_memory:.1f}GB)")
            
            return True
        else:
            print("  ❌ CUDA不可用")
            return False
            
    except ImportError:
        print("  ❌ PyTorch未安装")
        return False

def test_camera():
    """测试摄像头"""
    print("\n📹 摄像头检查:")
    
    try:
        import cv2
        
        # 尝试打开默认摄像头
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("  ✅ 摄像头可用 (设备ID: 0)")
            
            # 获取摄像头信息
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"  分辨率: {int(width)}x{int(height)}")
            print(f"  帧率: {fps}")
            
            cap.release()
            return True
        else:
            print("  ❌ 无法打开摄像头 (设备ID: 0)")
            return False
            
    except ImportError:
        print("  ❌ OpenCV未安装")
        return False

def test_file_structure():
    """测试文件结构"""
    print("\n📁 文件结构检查:")
    
    required_files = [
        "config.json",
        "app/config.py",
        "app/camera.py", 
        "app/extractor.py"
    ]
    
    required_dirs = [
        "models",
        "shots"
    ]
    
    all_good = True
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - 不存在")
            all_good = False
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/ - 不存在")
            all_good = False
    
    # 检查模型目录
    model_path = Path("models/qwen-3b")
    if model_path.exists():
        print(f"  ✅ models/qwen-3b/")
    else:
        print(f"  ⚠️  models/qwen-3b/ - 模型未下载")
        all_good = False
    
    return all_good

def test_config():
    """测试配置文件"""
    print("\n⚙️ 配置文件检查:")
    
    try:
        from app.config import Config
        config = Config()
        print("  ✅ 配置文件加载成功")
        
        # 验证关键配置
        print(f"  摄像头设备ID: {config.camera_device_id}")
        print(f"  模型路径: {config.model_path}")
        print(f"  输出目录: {config.shots_dir}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 配置文件加载失败: {e}")
        return False

def main():
    """主测试函数"""
    print("="*60)
    print("        财务单据识别工具 - 环境测试")
    print("="*60)
    
    results = []
    
    # 执行各项测试
    results.append(("Python版本", test_python_version()))
    
    deps_ok, missing = test_dependencies()
    results.append(("依赖包", deps_ok))
    
    results.append(("GPU配置", test_gpu()))
    results.append(("摄像头", test_camera()))
    results.append(("文件结构", test_file_structure()))
    results.append(("配置文件", test_config()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("        测试结果汇总")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name:15} {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统可以正常运行。")
    else:
        print("\n⚠️  部分测试失败，请根据上述信息修复问题。")
        
        if not deps_ok and missing:
            print("\n缺失的依赖包:")
            for pkg in missing:
                print(f"  pip install {pkg}")

if __name__ == "__main__":
    main() 