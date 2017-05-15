"""
GradeFast is a Python and JavaScript program to speed up your grading of programming projects.
See README.md for more information.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

__author__ = "Jake Hartz"
__copyright__ = "Copyright (C) 2017 Jake Hartz"
__license__ = "MIT"
__version__ = "0.9"

import os
import sys

_EXTERNAL_MODULES = ("iochannels", "pyprovide")

# Insert the folder containing each external module into the module search path
_GRADEFAST_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
for _m in _EXTERNAL_MODULES:
    sys.path.insert(1, os.path.join(_GRADEFAST_REPO_ROOT, "external", _m))


def required_package_error(module_name: str, package_name: str = None) -> None:
    if not package_name:
        package_name = module_name
    required_package_warning(
        module_name,
        "Please install '" + package_name + "' and try again.")
    sys.exit(1)


def required_package_warning(module_name: str, msg: str = None) -> None:
    print("==> Couldn't find", module_name, "module!")
    if msg:
        print("==>", msg)
