@echo off
chcp 65001 >nul
echo MathLessonGenerator を起動します...
pip install -r requirements.txt
python app.py
pause
