# GradeFast YAML Format

The GradeFast YAML format consists of 4 parts:

 - grades
 - submissions
 - commands

Although this is all detailed here with references to the YAML format, the only
module that actually parses YAML files is `__main__.py`. Some of the sections
below also apply to other modules in the project.

gradebook.py: "Grades section" (for any method that mentions "grade structure")

grader.py: "Submissions section" (for the add_submissions method),
           "Commands section" (for the run_commands method)

## Grades section

NOTE: Many of the strings in this section are **NOT** HTML-escaped before
getting thrown into a grade's feedback HTML. This is marked below as:
**HTML-parsed**

The grades section is composed of a list of grading items. Each item represents
an actual section of the grade, or a collection of other grading items. Each is
an associative array with one of the following sets of elements:

Actual section of grade:

 - `name` (string; **HTML-parsed**) - The name of the grading item
 - `points` (int) - The amount of points that this grading item is worth
 - `deductions` (list) - OPTIONAL - A list of common reasons for points being
   deducted from this grading item. Each list item is an associative array with
   a "name" (string; **HTML-parsed**) and a "minus" amount (int). NOTE: These
   values are not used to calculate actual scores; they are only used for
   feedback.

Collection of other grading items:

 - `name` (string; **HTML-parsed**) - The name of this section of grading items
 - `grades` (list) - A list of other grading items
 - `deductPercentIfLate` (int) - OPTIONAL - A value from 0 to 100 that indicates
   how much to deduct from this section if the submission is marked as late.

## Submissions section

The submissions section is composed of a list of submission folders. Each item
represents a directory full of folders of submissions. Each is an associative
array with the following elements:

 - `path` (string) - The path to the directory (either an absolute path or a
   path relative to the YAML file)
 - `regex` (string) - A regular expression used to match subdirectories of
   `path` that contain a submission. The first captured group (section in
   parenthesis) is used as the name of the submission.
 - `checkZipfiles` (boolean) - OPTIONAL (default: false) - Whether to check if
   any zipfiles in the directory also match `regex` (without the trailing
   `.zip`) and, if there isn't already a matching folder, extract the zipfiles.

## Commands section

The commands section is composed of a list of commands to run for each
submission. Each item represents either a command to run or a list of commands
to run, possibly in a subfolder. Each is an associative array with one of the
following sets of elements:

Actual command:

 - `name` (string) - An identifier for the command
 - `command` (string) - The actual command to run (run through the system shell)
 - `diff` (string) - OPTIONAL - A file to compare the output of the command to
   (either an absolute path or a path relative to the YAML file)

Collection of other commands:

 - `folder` (string or list) - Either a string representing a path to a
   subfolder, or a list of regular expressions representing subfolders.
 - `commands` (list) - Commands to run in the subfolder

By default (i.e. for top-level commands), the working directory is the folder at
the root of the submission it's running in.

Also, each command's environment contains the following environmental variables:

 - `SUBMISSION_DIRECTORY` - The path to the root directory for the current
   submission.
 - `CURRENT_DIRECTORY` - The path to the subfolder of the submission's root
   directory that we are working out of.
 - `SUBMISSION_NAME` - The name of the current submission.
 - `HELPER_DIRECTORY` - The path to the location of the YAML file (if started
   through __main__.py)

# Example

    ---
    grades:
    - name: Problem Solving
      points: 15
    - name: Attendance
      points: 5
    - name: Functionality
      deductPercentIfLate: 20
      grades:
      - name: "Part 1: Class"
        points: 20
        deductions:
        - name: "Missing constructor"
          minus: 5
        - name: "Private state not properly encapsulated"
          minus: 10
      - name: "Part 2: Main Method"
        points: 10
        deductions:
        - name: "[0] should output 1.0"
          minus: 3
        - name: "[1] should be True"
          minus: 2
        - name: "[2] should be False"
          minus: 1
      - name: "Part 3: Test Cases"
        points: 15
        deductions:
        - name: "Not enough test cases"
          minus: 5
        - name: "Not enough test cases"
          minus: 10
        - name: "First test case failed"
          minus: 5
        - name: "Second test case failed"
          minus: 5
      - name: Code Style
        points: 35

    submissions:
      # The directory full of folders for each submission.
    - path: "C:\\Users\\Me\\Downloads\\Lab1 Download"
      # The regular expression to match with the folders.
      regex: "^[0-9]+-[0-9]+ - (.+) - .+$"

    commands:
    - name: Test Opener
      command: echo "Hey, there!"
    - folder: ["^[A-Za-z]{3}[0-9]{4}$"]
      commands:
      - name: Setup
        command: "cp -R $HELPER_DIRECTORY/template . && mv Poly{String,Eval,Derive,Root}.java poly/stu/"
      - name: Compile PolyTest
        command: "javac -Xlint PolyTest.java"
      - name: Run PolyTest
        command: "java PolyTest"
        diff: "polytest-expected-output.txt"
      - name: View Code
        command: "vim -p poly/stu/Poly{Eval,Derive,Root}.java"
    - name: Test Closing
      command: "echo 'All done!'"

