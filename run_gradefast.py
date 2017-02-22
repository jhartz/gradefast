#!/usr/bin/env python3
"""
Runs the GradeFast module, for use in environments where we can't just do:
    python -m gradefast [args]
Instead, we can do:
    python run_gradefast.py [args]

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import sys
import os
import runpy

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, "..")
sys.path.insert(0, path)
runpy.run_module("gradefast", run_name="__main__", alter_sys=True)
