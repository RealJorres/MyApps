@echo off
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Starting PDF ^<-^> Image Converter...
echo Open http://localhost:5001 in your browser
echo Press Ctrl+C to stop
echo.
python app.py
pause
