#!/usr/bin/env python3
"""
GradeFast is a Python and JavaScript program to grade lots of programming labs or similar projects.

The Grader class controls the grading process. The GradeBook UI is handled in the gradebook module.

To use a YAML file as input, use the run function. The YAML file details the structure of the
grading and the commands to run. For more, see README.md.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from .grader import Grader
from .gradebook import *
from .runyaml import run

__author__ = "Jake Hartz"
__copyright__ = "Copyright (C) 2017 Jake Hartz"
__license__ = "MIT"
__version__ = "0.9"
