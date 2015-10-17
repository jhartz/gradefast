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
