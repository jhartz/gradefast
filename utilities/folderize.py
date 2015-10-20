"""
For labs which were supposed to be submitted as .zip files, but the students
submitted multiple flat files.

Creates a folder based on their name that matches what gradefast expects,
and moves all of the flat files into that folder.
"""
ext = "\.py" # regex fragment for the filetype

import os
import re
for file in os.listdir():
    matchObject = re.match("^[0-9]+-[0-9]+ - (.+) - (.+" + ext + ")$", file)
    if (matchObject is not None):
        foldername = matchObject.group(1)
        foldername = "0-0 - {} - a.zip".format(foldername)
        if (not os.access(foldername, os.F_OK)):
            os.mkdir(foldername)
        os.rename(file, foldername + "\\" + matchObject.group(2))
