@echo off
cd /d "%~dp0"
echo ========================================
echo View Uploaded Company List Content
echo ========================================
echo.
python view_uploaded_content.py
if errorlevel 1 (
    echo.
    echo Script encountered an error.
    pause
)

