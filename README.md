# GradeFast

*Automate and speed up your grading*

GradeFast is a Python/JavaScript program that eliminates the repetitive parts
of grading programming assignments and lets you focus on what's important:
helping students learn from their mistakes. Best of all, it lets you help them
without putting much time into it!

## Dependencies

### Python

GradeFast requires **Python *3.4*** or later!

Additionally, these packages are required:

 - [Colorama](https://pypi.python.org/pypi/colorama) to make it look pretty
 - [YAML](https://pypi.python.org/pypi/PyYAML) to... I don't know... parse the
   input files, or something silly like that
 - [Mistune](https://pypi.python.org/pypi/mistune/) to parse markdown
 - [Flask](https://pypi.python.org/pypi/Flask) because... what isn't shipped
   with a web server these days?
 - [pyreadline](https://pypi.python.org/pypi/pyreadline) (OPTIONAL) - if you
   want autocomplete support but your system doesn't have GNU readline (e.g.
   Windows and Mac OS X). Even with this module, readline support is still
   rather buggy on non-GNU-like platforms.

### JavaScript

The frontend UI is browser-based. To compile the JavaScript files, you will
need a working install of [Node.js](https://nodejs.org/) and
[NPM](https://www.npmjs.com/).

To install the Node dependencies and compile the JavaScript files, run:

    npm install
    npm run build

## Usage

Before running GradeFast, you need to compile the JavaScript components (see
the JavaScript dependencies above).

Then, to start GradeFast, run:

    python3 -m gradefast YAML_FILE [HOSTNAME [PORT]]

or, for more detailed usage:

    python3 -m gradefast

## But... how do I use this thing?

First, you must make a YAML file for whatever you want to grade that includes
the structure of the grades and the commands to run on each submission.
For more info, see the
[YAML Format page](https://github.com/jhartz/gradefast/wiki/YAML-Format)
on the GradeFast wiki.

Want to delve deeper or use individual parts of GradeFast as part of your
larger, superior project? Check out the `runyaml.py` module to see how the
other GradeFast modules and packages are used. Also, look at the
[other pages on the GradeFast wiki](https://github.com/jhartz/gradefast/wiki)
for lots more information.

## License

Licensed under the MIT License. For more, see the `LICENSE` file.
