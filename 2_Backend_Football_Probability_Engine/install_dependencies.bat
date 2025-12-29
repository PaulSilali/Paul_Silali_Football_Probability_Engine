@echo off
REM Install dependencies for Football Probability Engine Backend
REM This script installs packages in the correct order to avoid build issues

echo Installing dependencies...
echo.

REM Upgrade pip first
echo [1/4] Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install NumPy first (has pre-built wheels)
echo [2/4] Installing NumPy...
pip install numpy
echo.

REM Install other scientific packages
echo [3/4] Installing scientific packages...
pip install scipy pandas scikit-learn
echo.

REM Install all other dependencies
echo [4/4] Installing remaining dependencies...
pip install -r requirements.txt
echo.

echo Installation complete!
echo.
echo You can now run: npm run dev
pause

