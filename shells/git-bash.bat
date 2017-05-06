@echo off

REM This file exists so you can use it as the "shell" option for GradeFast
REM on Windows to process all commands through Git Bash.
REM Example:
REM   python -m gradefast --shell=shells/git-bash.bat ...
REM This is equivalent to:
REM   python -m gradefast --shell=path-to-bash.exe --shell-arg=-c

"C:\Program Files\Git\bin\bash.exe" -c %1
