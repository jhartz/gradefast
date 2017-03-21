# GradeFast

*Automate and speed up your grading*

GradeFast is a Python program (with an HTML/JavaScript UI) that eliminates the repetitive parts of
grading programming assignments and lets you focus on what's important: helping students learn from
their mistakes. Best of all, it lets you help them without putting much time into it!

## Dependencies

### Python

GradeFast requires **Python *3.6*** or later! (We use type hints.)

Additionally, these packages are required:

 - [YAML](https://pypi.python.org/pypi/PyYAML) to... I don't know... parse the input files, or
   something silly like that
 - [Flask](https://pypi.python.org/pypi/Flask) because... what doesn't ship with a web server these
   days?

Optional (but recommended) dependencies:

 - [Colorama](https://pypi.python.org/pypi/colorama) to make the CLI look pretty
 - [Mistune](https://pypi.python.org/pypi/mistune/) to parse Markdown in comments and feedback


### JavaScript

The GradeBook user interface is browser-based (HTML/JavaScript). To compile the JavaScript files,
you will need a working install of [Node.js](https://nodejs.org/) and [NPM](https://www.npmjs.com/).

To install the Node dependencies and compile the JavaScript files, run:

    npm install
    npm run build

## Usage

Before running GradeFast, you need to compile the JavaScript components (see the JavaScript
dependencies above).

Then, to start GradeFast, run:

    python3 -m gradefast YAML_FILE [HOSTNAME [PORT]]

or, for more detailed usage:

    python3 -m gradefast

## But... how do I use this thing?

See the [GradeFast wiki](https://github.com/jhartz/gradefast/wiki).

**tl;dr:** First, you must make a YAML-formatted configuration file the assignment that you want to
grade. This file includes the structure of the grades and the commands to run on each submission.
For more info, see the [YAML Format page](https://github.com/jhartz/gradefast/wiki/YAML-Format) on
the GradeFast wiki.

Want to delve deeper or use individual parts of GradeFast as part of your larger, superior project?
Check out the `runyaml.py` module to see how the other GradeFast modules and packages are used.
Also, look at the [other pages on the GradeFast wiki](https://github.com/jhartz/gradefast/wiki) for
lots more information.

## Bugs

Want to fix it yourself? (Please?) Fork the repository and submit a pull request on GitHub.
(Be sure to follow the [code style](STYLE.md).)

If that's too much work, feel free to file an issue on GitHub or email Jake Hartz.

## License

Licensed under the MIT License. For more, see the `LICENSE` file.

## Contact

Questions? Concerns? Feedback? Contact Jake Hartz.
