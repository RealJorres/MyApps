@echo off
echo Installing launcher dependencies...
pip install flask requests -q
echo.
echo Starting App Library...
echo Open http://localhost:5000 in your browser
echo.
python app.py
pause
