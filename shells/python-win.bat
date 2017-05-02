@echo off

REM Use this script as the "--shell" option in GradeFast to have all commands
REM be parsed by a Python interpreter, as Python code.
REM Example:
REM   python -m gradefast --shell=shells/python-win.bat ...
REM This is equivalent to:
REM   python -m gradefast --shell=path-to-python.exe --shell-arg=-c ...

WHERE /Q python
IF ERRORLEVEL 0 (
    python -c %1
) ELSE IF EXIST C:\Python36\python.exe (
    C:\Python36\python.exe -c %1
) ELSE IF EXIST C:\Python35\python.exe (
    C:\Python35\python.exe -c %1
) ELSE IF EXIST C:\Python34\python.exe (
    C:\Python34\python.exe -c %1
) ELSE IF EXIST C:\Python33\python.exe (
    C:\Python33\python.exe -c %1
) ELSE IF EXIST C:\Python32\python.exe (
    C:\Python32\python.exe -c %1
) ELSE IF EXIST C:\Python31\python.exe (
    C:\Python31\python.exe -c %1
) ELSE IF EXIST C:\Python30\python.exe (
    C:\Python30\python.exe -c %1
) ELSE IF EXIST C:\Python27\python.exe (
    C:\Python27\python.exe -c %1
) ELSE IF EXIST C:\Python26\python.exe (
    C:\Python26\python.exe -c %1
) ELSE IF EXIST C:\Python25\python.exe (
    C:\Python25\python.exe -c %1
) ELSE (
    ECHO No Python executable found
)
