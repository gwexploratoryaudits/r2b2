# r2b2 Library Design

[UML Diagram](https://drive.google.com/file/d/1S77bx7u6bc-EUuhpQ-BkAnYARJkoAJL0/view?usp=sharing)

- Class Structure UML Diagram

## Class Structure

The `Election` class encompasses all the information about election results that
are independent from an audit, the `Contest` class encompasses all the
information about a specific contest within an election, and the `Audit` class
takes an `Election` along with general audit parameters. Specific audit
implementations can be built as subclasses of the `Audit` class.

### Election

Class for containing information about any given election, independent from an
audit.

*Note*: This class is incomplete. Currently, an `Election` is simply created
from a list of contests and has no methods other than initialization. In the
future, it will be used within a larger structure which audits entire elections.


### Contest

Class to maintain necessary information about a specific contest within an
election.


**Notes:**
- The `Election` and `Contest` are linked in that an `Election` contains a list of its `Contest`s.


### Audit

An abstract class to define a *general* audit. It will define attributes and
methods common to all audits. In the future, it will provide frameworks for an
interactive audit execution and a 'bulk' execution given a data set.

For the most up-to-date version of the `Audit` class, look at
[r2b2/audit](https://r2b2.readthedocs.io/en/latest/autoapi/r2b2/audit/index.html)

*Note:* Some of the parameters will be provided by the users for each unique
audit, but others might be defined by developers in the audit sub-classes and be
constant values for each unique audit of that type.

#### Audits to be Implemented

- [X] Bayesian RLA
- [ ] Bayesian RLA with replacement
- [ ] BRAVO
- [ ] BRAVOlike
- [ ] Athena
- [ ] Minerva
- [ ] Metis


## Library File/Directory Hierarchy

Based on [cookiecutter-pylibrary](https://github.com/ionelmc/cookiecutter-pylibrary)
template

For library code:

```
./src/r2b2/         # Directory to contain library source code
    ./tests/        # Directory to contain tests within library source code
    __init__.py     
    __main__.py
    cli.py          # In case we ever want to implement a CLI
    ...
    election.py     # Election class definition
    contest.py      # Contest class definition
    audit.py        # Abstract audit class definition  
    bravo.py        # BARVO implemented as subclass of audit
    ...
```


# Proposed Code Development Plan


## Style Guide

All code for the library will be written in Python 3.7 and follow the
[PEP8](https://www.python.org/dev/peps/pep-0008/) style guide. Below is a short
summary of the most important concepts to follow with some clarifications
(for the purposes of this library) on the ambiguous portions of PEP8.

**Purpose**: The purpose of a style guide is 1) consistency and 2) readability.

### Formatting

Indentation levels should be 4 spaces wide. The preferred indentation character
in Python is a space, rather than a tab; however, if you prefer to use the tab
key (like a rational person) use an editor which will convert a tab character
into 4 spaces. *If you are going to use the tab key ensure the editor is using
4 spaces instead of the tb character because Python 3 does not allow the mixing
of tabs and spaces.*

The traditional maximum line length is 79 characters for code and 72 for blocks
of texts (such as docstrings, comments, etc.). These standards were created to
allow for two files to fit side-by-side on a display; however, now most monitors
and displays are wide enough to fit more than 160 characters across. As such,
this standard will be relaxed to 100.

**Blank Lines**

| Code | No. of Blank Lines |
|:---  | :---               |
| Top level function | 2 |
| Class Definition | 2 |
| Methods w/ classes | 1 |
| Logical sections w/ methods | 1-2 |


Imports should follow the order:

1. Standard library imports
2. Related 3rd party imports
3. Local library specific imports

```python
# Place imports on their own lines
import os
import sys

# Submodules may be combined
from math import floor, ceil

# Absolute imports are best if possible
# especially for imports within your own library
import mypkg.siblin
from mypkg import sibling2
from mypkg.sibling import example
```

**White Space**

- DO: Place 1 space immediately after commas, semicolons, and colons
  - *Note*: Avoid placing spaces around colons which act like a binary operator
  (e.g. `arr[1:9]`)
- DO NOT: Place spaces after an opening brace or before a closing brace.
- DO NOT: Place a space before the opening parenthesis of a function call or
the opening bracket for indexing/slicing
- DO: Place 1 space on each side of arithmetic and assignment operators
- DO NOT: Place more than 1 space before or after assignments operators, i.e.
do not align `=` vertically when assigning variable values
- DO NOT: Place spaces around the `=` sign when using with keyword arguments to
a function
- DO NOT: Leave trailing white spaces at the end of lines or in blank lines


**Quotes**

Use double quotes: `"your string"` for strings, `"""comment"""` for comments.


### Documentation

*Note: this only covers how documentation within code should be formatted, for
information on how documentation for the library will be developed see
[below](#library-documentation).*

**Comments** should be complete sentences used to elaborate on the code.

- Block comments (1 or more lines each beginning with a `# `) should be indented
to match the code that *follows* them.
- Inline Comments (a comment on the same line as the code) should be at least 2
spaces away from the statement and server a purpose. They should disambiguate
the line of code, either in function or intended purpose.
- Use `TODO` and `FIXME` in comments to document future work.


**Documentation Strings** should follow the
[Google Style](http://google.github.io/styleguide/pyguide.html) guidelines and
be compatible with [Sphinx](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html). Below are some examples of what different docstrings *might*
look like.

**Class**
```python
"""One line class description.

Longer explanation...
...

Attributes:
    attr1: I am the first attribute for this class.
"""
```

**Method**
```python
"""One line function description.

Longer explanation...
...

Args
    arg1 (int): I am an integer argument.
    arg2 (str): I am a string argument.
    arg3: I am argument without a type specified.

Returns:
    bool: This function returns a boolean.

Raises:
    TypeError: explanation of error.
"""
```

### Naming

| Name Type | Convention | Notes |
| :---      | :---       | :---  |
|Package, Module | `shortlowcase` | Underscores can be used for readability |
|Class | `CapWords` | |
| Type Variable | `CapWords_suffix`| |
| Global Variables | `low_case_sep`| |
| Functions | `low_case_sep`| |
| Function Variables | `low_case_sep`| |
| Function Arguments | `low_case_sep` | Use underscores sparingly |
| Constants | `ALL_CAPS` | |

## Development Environment

Use `pip install -r docs/requirements.txt`, or if you have multiple versions of
Python installed, `python3 -m pip install -r docs/requirements.txt` to get
started setting up your development environment.

**TODO:** update `requirements.txt`

The library will be written in Python 3.7, so use this version when developing.
To see what version you currently have installed, run `python3 --version`. If
the output is `Python 3.7.x`, you are good to go! Otherwise,
[install](https://www.python.org/downloads/).

Code can be linted using [flake8](https://flake8.pycqa.org/en/latest/index.html),
just ensure it is installed for the correct version of Python (i.e. 3.7).

To make standard formatting easy and consistent, the auto formatting tool
[yapf](https://github.com/google/yapf) should be used.

*Note:* `flake8` and `yapf` will not ensure that all of the standards for this
library are met&mdash;It is your responsibility to do so.

Use any editor you want! An [EditorConfig](https://editorconfig.org/) file
(`.editorconfig`) is provided to help configure supported editors. Simply
ensure that your editor will not interfere with any of the standards outlined
above. If linting is enabled, ensure the linter is `flake8` and if possible,
modify its configuration to match the one presented in `setup.cfg`.
Some editors can integrate `yapf` as a plugin&mdash;this is highly recommended.

## Library Documentation

Current documentation [here](https://r2b2.readthedocs.io/en/latest/)

[Sphinx](https://www.sphinx-doc.org/en/master/) and
[ReadTheDocs](https://docs.readthedocs.io/en/latest/index.html) will be used to
generate well-formatted documentation for the library.

**TODO** add to section.

## Testing

We use [tox](https://tox.readthedocs.io/en/latest/) for cross-platform testing
and continuous integration. We aim for nearly complete code coverage in our
tests, generally implemented via [pytest](https://docs.pytest.org/en/latest/)
for doctests, and tracked at our
[Codecov](https://codecov.io/github/gwexploratoryaudits/r2b2) page.

**TODO** add to this section.

## Basic Workflow Notes

**Repository**

- The main repository is [r2b2](https://github.com/gwexploratoryaudits/r2b2)
- **Branches** are for individual features or project sections
  - Preferably, multiple people will not be working heavily on the same branch
  at the same time
  - If you get carried away and realize you are working on functionality that
  does not belong on the current branch, **git stash** it for later.


**Pushing, Merging, and Pulling**

- **Commit** messages should have a short one-line summary of 50 characters or
less, followed by a detailed description of changes made
  - Commits should be modular (e.g. a complete method, passing current tests,
      passing linter)
  - Commits should **never** contain commented out code or print statements
  (unless of course those print statements are intended functionality) that were
  used for *personal* debugging purposes.
    - The [Logging facility for Python](https://docs.python.org/3/library/logging.html)
    should be used for debugging rather than print statements.
  - Ensure you commit code that is properly formatted (run `yapf`) and
  documented.
  - It is not entirely necessary that new functionality be fully tested; however,
  all tests that were previously passing should still pass.
- **Push** to the current working branch about as frequently as you commit.
- Open a **Pull Request** when:
  - A significant amount of functionality has been added to current branch.
  - Prefix the title of the PR with `WIP: ` until the above standards are met
  and it is ready for review.
  - Include a message with a summary of changes, but do not write a book, the
  message along with the included commits should clearly explain what has
  happened for reviewers.
- **Merging**:
  - DO NOT merge your own PR without any review
  - At least 1 other contributor, if not more must review your PR before a merge
  - The repository is configured to require that pull requests apply cleanly, so
  `git rebase origin/master` your changes to the latest master if necessary.
