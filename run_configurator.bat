echo on
echo ========================================
echo PU Observatory - Configurator App
echo ========================================
echo.
echo Starting Configurator...
echo.
cd /d "%~dp0"
streamlit run configurator_app.py --server.port 8501
echo.
echo ========================================
echo Configurator stopped.
echo ========================================
pause

