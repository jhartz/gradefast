# GradeFast

Python program to grade lots of programming labs or similar projects.

## Dependencies

GradeFast requires **Python *3.4*** or later!

Additionally, these packages are required:

 - [Colorama](https://pypi.python.org/pypi/colorama) to make it look pretty
 - [YAML](https://pypi.python.org/pypi/PyYAML) to... I don't know... parse the
   input files, or something silly like that
 - [Mistune](https://pypi.python.org/pypi/mistune/) to parse markdown
 - [Flask](https://pypi.python.org/pypi/Flask) because... what isn't shipped
   with a web server these days?

### Optional Dependencies

 - [pyreadline](https://pypi.python.org/pypi/pyreadline) - if you want
   autocomplete support but your system doesn't have GNU readline (e.g.
   Windows and Mac OS X). Even with this module, readline support is still
   rather buggy on non-GNU-like platforms.

Also, use Python 3 (in case you, like me, still live in ye olden days of
having `python` symlinked to Python 2)

## Usage

    python3 -m gradefast YAML_FILE [HOSTNAME [PORT]]

or, for more detailed usage:

    python3 -m gradefast

## But... how do I use this thing?

First, you must make a YAML file for whatever you want to grade that includes
the structure of the grades and the commands to run on each submission.
For more info, see the
[YAML Format page][https://github.com/jhartz/gradefast/wiki/YAML-Format]
on the GradeFast wiki.

Want to delve deeper or use individual parts of GradeFast as part of your
larger, superior project? Check out the individual `grader.py`, `gradebook.py`,
and `runyaml.py` modules. Also, look at the
[other pages on the GradeFast wiki][https://github.com/jhartz/gradefast/wiki]
for lots more information.

## License

Licensed under the MIT License. For more, see the `LICENSE` file.
