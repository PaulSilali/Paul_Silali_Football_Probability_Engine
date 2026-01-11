@echo off
echo ========================================
echo COMPREHENSIVE SYSTEM TEST RUNNER
echo ========================================
echo.

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo ========================================
echo Running Comprehensive System Tests...
echo ========================================
python comprehensive_system_test.py

echo.
echo ========================================
echo Running Frontend Integration Tests...
echo ========================================
python frontend_integration_test.py

echo.
echo ========================================
echo All tests completed!
echo ========================================
pause

