echo on
echo ========================================
echo PU Observatory - Generator App
echo ========================================
echo.
echo Starting Newsletter Generator...
echo.
cd /d "%~dp0"
streamlit run generator_app.py --server.port 8503
echo.
echo ========================================
echo Generator stopped.
echo ========================================
pause

