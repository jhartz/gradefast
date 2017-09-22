# GradeFast utilities

## `dump-save-file.py`

Dump the contents of a GradeFast save file as one of:
- JSON
- YAML
- Tagged YAML

See https://github.com/jhartz/gradefast/wiki/Save-Files for more information about GradeFast save
files.

## `GradeFast to myCourses.user.js`

A userscript to put GradeFast grades into RIT myCourses. For more, see the documentation at the top
of the file.

## `folderize.py`

Sometimes, labs are supposed to be submitted as .zip files, but students make several independent
submissions of flat source files. This script fixes that. At the end of script execution, the
folder structure will be as if the students had made correct submissions, and you had already
unzipped their .zip file into a subdirectory.

You may wish to deduct points anyways. This script makes the minimal folder name which will match
the regex in the [example YAML file](https://github.com/jhartz/gradefast/wiki/YAML-Format#example).
Thus, the prefix will be 0-0, allowing you to determine which folders were submitted correctly and
which are the result of this script.

### Directory structure example

before:

    12345-1234567 - Doe, John - source1.py
    12345-1234567 - Doe, John - source2.py

after:

    0-0 - Doe, John - a
       source1.py
       source2.py
