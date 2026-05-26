@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
echo Starting bot... > bot_out.txt
python bot.py >> bot_out.txt 2>&1
