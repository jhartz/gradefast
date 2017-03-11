# GradeFast code style

ALWAYS ALWAYS ALWAYS:
- Indentation is **4 *spaces***

## Python code

In general, follow [PEP 8](https://www.python.org/dev/peps/pep-0008/).

In addition to PEP 8:

- Always use double quotes for string literals, UNLESS:
    - The string contains a double quote, and it looks cleaner to use single quotes, OR
    - The string contains raw HTML
- The line length cut-off is 100 characters (don't feel constrained to just 80).
- Always use Python [type hints](https://www.python.org/dev/peps/pep-0484/) for function arguments
  and return types. Feel free to use the built-in
  [typing](https://docs.python.org/3/library/typing.html) library.
- Always use docstrings for both classes and functions (unless the function is overriding another
  already-documented function from a superclass).

  Docstring format:
    - General description of the function
    - *blank line*
    - `:param` descriptions of each parameter
    - `:return` description of the return value, if applicable
- Imports at the top of each file should follow this general order:
    - `import` statements (ordered alphabetically by module name)
    - *blank line*
    - `from ... import ...` statements (ordered alphabetically by module name)
    - *blank line*
    - Local imports
    - *blank line*
    - Any imports wrapped in a `try`/`except`

## JavaScript code

- Try to match the existing style where possible.
- Prefer using `let` or `const` over `var`.
- Try to document functions using [JSDoc](http://usejsdoc.org/) comments. Be sure to include types
  for arguments.
- Imports at the top of each follow should follow this general order:
    - Any global imports (React, etc.)
    - *blank line*
    - Any imports from the root `js` directory (ordered alphabetically by filename)
    - blank line
    - Any imports from the file's directory (ordered alphabetically by filename)
