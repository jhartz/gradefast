#!/usr/bin/env python3
"""
Python program to grade lots of programming labs or similar projects.

The class Grader controls the grading process.

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
