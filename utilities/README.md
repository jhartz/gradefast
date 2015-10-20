# GradeFast utilities

## `GradeFast to myCourses.user.js`

A userscript to put GradeFast grades into RIT myCourses. This requires that
the GradeFast server be running (it sends a request to the server to get the
JSON grade data).

To use this userscript, install either GreaseMonkey in Firefox or TamperMonkey
in Chrome. Then, on myCourses grade entry pages
(`https://mycourses.rit.edu/d2l/lms/grades/admin/enter/*`), you should see a
new button in the sticky footer titled "Insert next GradeFast grade". Click
this to begin.

After it enters each grade and the corresponding feedback, you should look it
over, then click Save. Then, click "Insert next GradeFast grade" to continue
on to the next.

## `folderize.py`

Sometimes, labs are supposed to be submitted as .zip files, but students make
several independent submissions of flat source files. This script fixes that.
At the end of script execution, the folder structure will be as if the students
had made correct submissions, and you had already unzipped their .zip file into
a subdirectory.

You may wish to deduct points anyways. This script makes the minimal folder name
which will match the regex in the
[example YAML file](https://github.com/jhartz/gradefast/wiki/YAML-Format#example).
Thus, the prefix will be 0-0, allowing you to determine which folders were
submitted correctly and which are the result of this script.

### Directory structure example
before:

    12345-1234567 - Doe, John - source1.py
    12345-1234567 - Doe, John - source2.py
after:

    0-0 - Doe, John - a.zip
      source1.py
      source2.py
