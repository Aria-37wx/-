@echo off
cd /d "%~dp0"

echo ========================================
echo   物料管理系统 启动
echo ========================================
echo.
echo 正在启动 Web 服务 (http://localhost:8501)...
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [提示] 未找到 Python，请先安装 Python 并加入 PATH
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>nul
if errorlevel 1 (
    echo [提示] 未安装 streamlit，请运行：
    echo   python -m pip install "mcp>=1.0,<2" streamlit openai
    pause
    exit /b 1
)

python -m streamlit run warehouse_mcp\web\app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false
pause
