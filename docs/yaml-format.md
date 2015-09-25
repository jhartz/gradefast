# GradeFast YAML Format

The GradeFast YAML format consists of 4 parts:

 - grades
 - submissions
 - commands
 - config

Although this is all detailed here with references to the YAML format, the only
module that actually parses YAML files is `runyaml.py`. Some of the sections
below also apply to other modules in the project.

gradebook.py: "Grades section" (for any method that mentions "grade structure")

grader.py: "Submissions section" (for the add_submissions method),
           "Commands section" (for the run_commands method)

Within this document, "list" refers to a YAML sequence collection (or array) and
a "dictionary" refers to a YAML mapping collection (or associative array).

## Grades section

NOTE: Many of the strings in this section are parsed as Markdown, which means
that *not all HTML is escaped*. This is marked below as: **Markdown**

The grades section is composed of a list of grading items. Each item represents
an actual section of the grade, or a collection of other grading items. Each is
a dictionary that will have one of the following sets of elements:

*Actual section of grade:*

 - `name` (string; required; **Markdown**) - The name of the grading item.
 - `disabled` (boolean; optional) - Whether this grading item is disabled by
   default.
 - `points` (int; required) - The amount of points that this grading item is
   worth.
 - `point hints` (list; optional) - A list of common reasons for gaining extra
   points or losing points on this grading item. This assists the grader when
   determining the points. Each list item is a dictionary with a "name"
   (string; **Markdown**) and a "value" amount (int). To indicate losing
   points, the value should be a negative number. *NOTE: Unlike `deductions`
   below, these values are not used to calculate actual scores; they are only
   used for feedback.*
- `default points` (int; optional) - The default amount of points. If not
  provided, defaults to `points`.
- `default comments` (string; optional; **Markdown**) - Default comments for
  this grading item. If not specified, defaults to "".
- `note` or `notes` (string; optional; **Markdown**) - Any notes for the
  grader. These show up in the gradebook interface, but are never added to the
  feedback that is meant for the owner of the submission.

*Collection of other grading items:*

 - `name` (string; required; **Markdown**) - The name of this section of
   grading items.
 - `disabled` (boolean; optional) - Whether this section is disabled by default.
 - `grades` (list; required) - A list of other grading items.
 - `deductions` (list; optional) - A list of reasons for points being deducted
   from this grading section. Each list item is a dictionary with a "name"
   (string; **Markdown**) and a "minus" amount (int). *NOTE: Unlike `point
   hints` above, these ARE used in both calculating the score AND feedback!*
 - `deduct percent if late` (int; optional) - A value from 0 to 100 that
   indicates how much to deduct from this section if the submission is marked
   as late.
- `note` or `notes` (string; optional; **Markdown**) - Any notes for the
  grader. These show up in the gradebook interface, but are never added to the
  feedback that is meant for the owner of the submission.

## Submissions section

The submissions section is composed of a list of submission folders. Each item
represents a directory full of folders of submissions. Each is a dictionary
with the following elements:

 - `path` (string) - The path to the directory (either an absolute path or a
   path relative to the YAML file)
 - `regex` (string) - A regular expression used to match subdirectories of
   `path` that contain a submission. The first captured group (section in
   parenthesis) is used as the name of the submission.
 - `check zipfiles` (boolean) - OPTIONAL (default: false) - Whether to check if
   any zipfiles in the directory also match `regex` (without the trailing
   `.zip`) and, if there isn't already a matching folder, extract the zipfiles.

## Commands section

The commands section is composed of a list of commands to run for each
submission. Each item represents either a command to run or a list of commands
to run, possibly in a subfolder. Each is a dictionary with one of the
following sets of elements:

Actual command:

 - `name` (string) - An identifier for the command
 - `command` (string) - The actual command to run (run through
   `config["command shell"]` or the system's default shell)
 - `environment` (dictionary) - Environmental variables for this command
 - `diff` (string) - OPTIONAL - A file to compare the output of the command to
   (either an absolute path or a path relative to the YAML file)

Collection of other commands:

 - `folder` (string or list) - Either a string representing a path to a
   subfolder, or a list of regular expressions representing subfolders
 - `environment` (dictionary) - Environmental variables for these commands
 - `commands` (list) - Commands to run in the subfolder

Many times, a group of other commands is created with `folder` equal to `"."`.
This allows the user to see the files inside and possibly choose a different
location for the folder.

By default (i.e. for top-level commands), the working directory is the folder at
the root of the submission it's running in.

Also, each command's environment contains the following environmental variables:

 - `SUBMISSION_DIRECTORY` - The path to the root directory for the current
   submission.
 - `CURRENT_DIRECTORY` - The path to the subfolder of the submission's root
   directory that we are working out of.
 - `SUBMISSION_NAME` - The name of the current submission.
 - `HELPER_DIRECTORY` - The path to the location of the YAML file (if started
   through runyaml.py)

## Config section

This section has miscellaneous configuration options. Unlike the others, it is
not a list, but rather just a dictionary.

It can have any of these properties:

 - `save file` (string) - The path to the file to save the grade data in. If
   the path is relative, it is resolved relative to the YAML file. If not
   provided, then no save file is created. This file is also checked on startup
   to pick up where we left off (if possible). **NOTE: The contents of these
   save files are parsed and created by Python's
   [pickle](https://docs.python.org/3/library/pickle.html) library. *MALICIOUS
   FILES COULD RUN ARBITRARY CODE!* Make sure that you trust a file before
   specifying it here.**
 - `terminal shell` (list) - A command to run to open a terminal/command prompt
   window in a certain directory. (See "Commands" below for format of list.)
   Within the list, a list item (i.e. argument) with a value of `null` will be
   replaced with the path to open. Also, the current working directory will be
   set to the directory to open.
 - `command shell` (list) - A command to run to execute the commands in the
   "command" section. (See "Commands" below for format of list.) Within the
   list, a list item (i.e. argument) with a value of `null` will be replaced
   with the shell command to execute.

### Commands in the Config section

In the config section, commands (for "terminal shell" and "command shell") must
be specified as lists. The first item is the program to run and the rest are
arguments to the program.

These commands also specify that a value of `null` should be used to indicate
where the variable arg should be. Null can be indicated `null`, `Null`, `NULL`,
or `~` in YAML.

# Example

    ---
    grades:
    - name: Problem Solving
      points: 15

    - name: Attendance
      points: 5

    - name: Functionality
      deduct percent if late: 20
      deductions:
      - name: "Not enough test cases"
        minus: 5
      - name: "Not enough test cases"
        minus: 10
      - name: "First test case failed"
        minus: 5
      - name: "Second test case failed"
        minus: 5
      grades:
      - name: "Part 1: Class"
        points: 20
        point hints:
        - name: "Missing constructor"
          value: -5
        - name: "Private state not properly encapsulated"
          value: -10
      - name: "Part 2: Main Method"
        points: 10
        default points: 4
        point hints:
        - name: "[0] outputs 1.0"
          value: 3
        - name: "[1] is True"
          value: 2
        - name: "[2] is False"
          value: 1
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
      environment:
        # Add an environmental variable to the environment for all these
        # sub-commands
        IN_PROJECT: my grading project
      commands:
      - name: Setup
        command: >
          cp -R $HELPER_DIRECTORY/template . &&
          mv Poly{String,Eval,Derive,Root}.java poly/stu/
      - name: Compile PolyTest
        command: "javac -Xlint PolyTest.java"
      - name: Run PolyTest
        command: "java PolyTest"
        # Compare the output against this diff file
        diff: "polytest-expected-output.txt"
      - name: View Code
        command: "vim -p poly/stu/Poly{Eval,Derive,Root}.java"
    - name: Test Closing
      command: "echo 'All done!'"

    config:
      # Save file relative to the YAML file
      save file: "yaml test.data"
      # Parse commands using git bash (MinGW) rather than cmd
      command shell: ["C:\\Program Files (x86)\\Git\\bin\\bash.exe", "-c", ~]
      # Open bash terminals instead of normal windows command prompts
      terminal shell:
      - "cmd"
      - "/C"
      - "start C:\\PROGRA~2\\Git\\bin\\bash.exe --login"

