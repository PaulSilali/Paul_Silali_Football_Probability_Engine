@echo off
echo ============================================================
echo Fixing .env file parsing issues
echo ============================================================
echo.
cd /d "%~dp0"
python check_and_fix_env.py
echo.
echo ============================================================
echo Done! Please restart your backend server.
echo ============================================================
pause

