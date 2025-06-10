@echo off
chcp 65001 > nul
echo ============================================================
echo            财务单据自动抓拍识别工具 v1.0 RC
echo ============================================================
echo.

REM 检查Python是否存在
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    echo 请先安装Python 3.10+并添加到系统PATH
    pause
    exit /b 1
)

REM 检查虚拟环境是否存在
if not exist "venv\" (
    echo 🔧 创建Python虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
echo 🚀 激活虚拟环境...
call venv\Scripts\activate.bat

REM 检查依赖是否安装
echo 📦 检查依赖...
python -c "import torch, cv2, transformers" > nul 2>&1
if errorlevel 1 (
    echo ⚠️  缺少必要依赖，正在安装...
    echo 这可能需要几分钟时间...
    pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
)

REM 运行环境测试
echo 🧪 运行环境测试...
python test_env.py
if errorlevel 1 (
    echo.
    echo ⚠️  环境测试发现问题，请根据上述信息修复后重新运行
    pause
    exit /b 1
)

echo.
echo ✅ 环境检查通过，启动主程序...
echo.
echo 操作提示：
echo   • 按 ESC 键（在摄像头窗口）退出程序
echo   • 按 Ctrl+C （在此窗口）强制退出
echo   • 将票据放在摄像头视野内即可自动识别
echo.

REM 启动主程序
python main_final.py

echo.
echo 程序已退出。
pause 