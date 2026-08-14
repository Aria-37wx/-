@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   物料管理系统 启动
echo ========================================
echo.
echo 启动 Web 服务 (http://localhost:8501)...
call C:\Anaconda\envs\py312\Scripts\streamlit.exe run warehouse_mcp\web\app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false
pause
