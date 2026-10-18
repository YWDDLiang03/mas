@echo off
python "%~dp0scripts\agent_run.py" --bootstrap %*
exit /b %errorlevel%
