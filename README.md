# GradeFast

Python program to grade a shitton of CS labs or something similar.

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
   Windows and Mac OS X)

Also, use Python 3 (in case you, like me, still live in ye olden days of
having `python` symlinked to Python 2)

## Usage

    python3 -m gradefast YAML_FILE [HOSTNAME [PORT]]

or, for more detailed usage:

    python3 -m gradefast

## But... how do I use this thing?

Look in the `docs/` folder for the YAML spec. Use that to make your own YAML
file representing the shit you want to grade.

Want to delve deeper or use individual parts of GradeFast as part of your
larger, superior project? Check out the individual `grader.py`, `gradebook.py`,
and `runyaml.py` modules, and look in `__main__.py` to see how they're used.

## I think your program is shitty

Then help me improve it. I guarantee you, this isn't the most thought-out
project.

## License

Licensed under the MIT License. For more, see the `LICENSE` file.
