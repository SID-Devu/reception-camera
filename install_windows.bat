@echo off
REM Windows installation script for Reception Greeter
REM This script handles the insightface build issue on Windows with Python 3.12
REM by using prebuilt binaries instead of compiling from source

echo ========================================
echo Reception Greeter - Windows Setup
echo ========================================

REM Check if venv is activated
if not defined VIRTUAL_ENV (
    echo.
    echo ERROR: Virtual environment not activated!
    echo Please activate your venv first:
    echo   .venv\Scripts\activate
    echo.
    exit /b 1
)

echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat 2>nul || (
    echo ERROR: Could not activate venv at .venv
    exit /b 1
)

echo.
echo Detected Python version:
python --version

echo.
echo Installing dependencies with prebuilt binaries (--prefer-binary)...
echo This avoids C++ compilation issues with insightface on Windows.
echo.

pip install --prefer-binary ^
    opencv-python ^
    numpy ^
    insightface ^
    onnxruntime ^
    scipy ^
    pyttsx3 ^
    PyYAML ^
    albumentations==1.4.24

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed!
    exit /b 1
)

echo.
echo ========================================
echo ✅ Installation complete!
echo ========================================
echo.
echo Next step: Download face recognition models
echo   python tools/download_models.py
echo.
echo Then run the system:
echo   python app/main.py --config app/config.yaml
echo.
