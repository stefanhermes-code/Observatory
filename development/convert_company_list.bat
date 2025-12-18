@echo off
echo ========================================
echo Company List Converter
echo ========================================
echo.

REM Check if file was dragged onto the batch file
if not "%~1"=="" (
    set INPUT_FILE=%~1
    echo Using file: %INPUT_FILE%
    echo.
    python development/convert_company_list_txt.py "%INPUT_FILE%"
    echo.
    pause
    exit /b
)

REM Interactive mode - ask for file
echo Please enter the path to your company list text file.
echo (You can drag and drop the file onto this window, or type the path)
echo.
set /p INPUT_FILE="File path: "

if "%INPUT_FILE%"=="" (
    echo.
    echo No file specified. Exiting.
    pause
    exit /b
)

echo.
echo Converting...
python development/convert_company_list_txt.py "%INPUT_FILE%"
echo.
pause
