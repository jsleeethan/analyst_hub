@echo off
REM ============================================================
REM  Windows build script for Naver Report Viewer
REM  Produces: dist\NaverReportViewer.exe
REM
REM  Requirements:
REM    - Python 3.9+ installed and on PATH
REM ============================================================

setlocal
cd /d "%~dp0"

echo [1/4] Creating virtual environment...
if not exist venv_build (
    python -m venv venv_build || goto :error
)

call venv_build\Scripts\activate.bat || goto :error

echo [2/4] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt || goto :error
pip install pyinstaller || goto :error

echo [3/4] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [4/4] Building executable...
pyinstaller NaverReportViewer.spec || goto :error

echo.
echo ============================================================
echo  BUILD SUCCEEDED
echo  Output: %cd%\dist\NaverReportViewer.exe
echo ============================================================
goto :end

:error
echo.
echo ============================================================
echo  BUILD FAILED (exit code %errorlevel%)
echo ============================================================
exit /b 1

:end
endlocal
