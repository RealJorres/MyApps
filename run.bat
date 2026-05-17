@echo off
echo Installing dependencies...
pip install -r requirements.txt -q
echo.
echo Starting App Library...
echo Open http://localhost:5000 in your browser
echo.
python app.py
pause
