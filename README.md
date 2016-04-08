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

To compile the React JSX files, you will need a working install of
[Node.js](https://nodejs.org/) and [NPM](https://www.npmjs.com/). To install
the Node dependencies:

    npm install --global grunt-cli
    npm install  # to install other build requirements locally

Before running GradeFast, you must run `grunt` in the same directory as
`Gruntfile.js`.

### Optional Dependencies

 - [pyreadline](https://pypi.python.org/pypi/pyreadline) - if you want
   autocomplete support but your system doesn't have GNU readline (e.g.
   Windows and Mac OS X). Even with this module, readline support is still
   rather buggy on non-GNU-like platforms.

Also, use Python 3 (in case you, like me, still live in ye olden days of
having `python` symlinked to Python 2)

## Usage

Before running GradeFast, you need to build the JavaScript. To do this, run
`grunt` in the same directory as `Gruntfile.js`.

Alternatively, you can have grunt watch the JS files for changes and
automatically recompile them. To do this, run `grunt watchme`

Finally, to start GradeFast, run:

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
