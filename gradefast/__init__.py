#!/usr/bin/env python3
"""
Package to grade a shitton of CS labs or something similar.

The class Grader controls the grading process.

To use a YAML file as imput, use the run function. The YAML file details the
structure of the grading and the commands to run.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""

from .grader import Grader
from .gradebook import GradeBook
from .runyaml import run

__author__ = "Jake Hartz"
__copyright__ = "Copyright (C) 2015 Jake Hartz"
__license__ = "MIT"
__version__ = "0.9"

__all__ = ["Grader", "GradeBook", "run"]
