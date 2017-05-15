# GradeFast code style

ALWAYS ALWAYS ALWAYS:
- Indentation is **4 *spaces***

## Commit messages

- [Don't write bad commit messages][http://stopwritingramblingcommitmessages.com/].
- Follow [these formatting guidelines][http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html]
  (well, except for the part about grammar). Fun fact: a decent version of `vim` will automatically
  break lines for you (if you use it as your `EDITOR` for `git commit`).

## Python code

In general, follow [PEP 8](https://www.python.org/dev/peps/pep-0008/).

In addition to PEP 8:

- Always use double quotes for string literals, UNLESS:
    - The string contains a double quote, and it looks cleaner to use single quotes, OR
    - The string contains raw HTML

- The line length cut-off is 100 characters (don't feel constrained to just 80).

- Use `str.format` instead of `%`-style string formatting.

- Always use Python [type hints](https://www.python.org/dev/peps/pep-0484/) for function parameters
  and return types.
    - If a parameter has a default value of `None`, omit the `Optional[]` around the type.
    - Feel free to use the built-in [typing](https://docs.python.org/3/library/typing.html) library.
    - Prefer `Sequence` to `List` and prefer `Mapping` to `Dict` for function parameters that are
      not mutated.

- Always use docstrings for classes. When it is helpful, use docstrings for public methods too
  (unless the function is overriding another already-documented function from a superclass).

  Docstring format:
    - General description of the function
    - *blank line*
    - `:param` descriptions of each parameter
    - `:return` description of the return value, if applicable

- Imports at the top of each file should follow this general order:
    - `import` statements (ordered alphabetically)
    - `from ... import ...` statements (ordered alphabetically)
    - *blank line*
    - Imports from the "external" folder (e.g. pyprovide)
    - *blank line*
    - GradeFast imports (ordered alphabetically) - always absolute, starting with `gradefast.`
    - *blank line*
    - Any imports wrapped in a `try`/`except`

## JavaScript code

- Try to match the existing style where possible.
- Prefer using `let` or `const` over `var`.
- The soft line length limit is 100 characters, but it's okay to go over if it makes things
  prettier.
- Try to document functions using [JSDoc](http://usejsdoc.org/) comments. Be sure to include types
  for arguments.
- Imports at the top of each follow should follow this general order:
    - Any global imports (React, etc.)
    - *blank line*
    - Any imports from the root `js` directory (ordered alphabetically by filename)
    - *blank line*
    - Any imports from the file's directory (ordered alphabetically by filename)
