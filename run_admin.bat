echo on
echo ========================================
echo PU Observatory - Admin App
echo ========================================
echo.
echo Starting Admin Control Tower...
echo.
cd /d "%~dp0"
streamlit run admin_app.py --server.port 8502
echo.
echo ========================================
echo Admin app stopped.
echo ========================================
pause

