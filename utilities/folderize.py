"""
For labs which were supposed to be submitted as .zip files, but the students
submitted multiple flat files.

Creates a folder based on their name that matches what gradefast expects,
and moves all of the flat files into that folder.

NOTE: This functionality is now built in to GradeFast (see the "check file extensions" setting in
the YAML file).

Authors: Chris Lentner <chris@lentner.me>, Jake Hartz <jake@hartz.io>
"""

import os
import re

# Regex fragment for the filetype
EXT = "\.py"

for file in os.listdir():
    matchObject = re.match("^[0-9]+-[0-9]+ - (.+) - (.+" + EXT + ")$", file)
    if (matchObject is not None):
        foldername = matchObject.group(1)
        foldername = "0-0 - {} - a.zip".format(foldername)
        if (not os.access(foldername, os.F_OK)):
            os.mkdir(foldername)
        os.rename(file, os.path.join(foldername, matchObject.group(2)))
