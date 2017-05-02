#!/bin/sh
# Use this script as the "--shell" option in GradeFast to have all commands be
# parsed by a Python interpreter, as Python code.
# Example:
#   python -m gradefast --shell=shells/python.sh ...
# This is equivalent to:
#   python -m gradefast --shell=/usr/bin/python3 --shell-arg=-c ...

pyexec="$(which python3 2>/dev/null)"
if which python3 >/dev/null 2>&1; then
    pyexec="$(which python3)"
elif which python >/dev/null 2>&1; then
    pyexec="$(which python)"
else
    echo "ERROR: Python executable not found!"
    exit 1
fi

exec "$pyexec" -c "$1"

