@echo off
cd /d "%~dp0"

echo ========================================
echo   物料管理系统 启动
echo ========================================
echo.

rem Prefer py312 env (full deps), fallback to PATH python
set "PY=python"
if exist "C:\Anaconda\envs\py312\python.exe" set "PY=C:\Anaconda\envs\py312\python.exe"

"%PY%" -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo [提示] 未找到 Python，请先安装 Python 并加入 PATH
    pause
    exit /b 1
)

"%PY%" -c "import streamlit" >nul 2>nul
if errorlevel 1 (
    echo 首次运行，正在自动安装依赖，请稍候...
    "%PY%" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请手动执行：
        echo   "%PY%" -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo 正在启动 Web 服务 (http://localhost:8501)...
echo.
"%PY%" -m streamlit run warehouse_mcp\web\app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false
pause
