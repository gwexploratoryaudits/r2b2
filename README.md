# Overview

[![Documentation Status](https://readthedocs.org/projects/r2b2/badge/?version=latest)](https://r2b2.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/gwexploratoryaudits/r2b2.svg?branch=main)](https://travis-ci.org/gwexploratoryaudits/r2b2)
[![Requirements Status](https://requires.io/github/gwexploratoryaudits/r2b2/requirements.svg?branch=main)](https://requires.io/github/gwexploratoryaudits/r2b2/requirements/?branch=main)
[![Coverage Status](https://codecov.io/github/gwexploratoryaudits/r2b2/coverage.svg?branch=main)](https://codecov.io/github/gwexploratoryaudits/r2b2)
[![Commits since latest release](https://img.shields.io/github/commits-since/gwexploratoryaudits/r2b2/v0.1.0.svg)](https://github.com/gwexploratoryaudits/r2b2/compare/v0.1.0...main)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


Round-by-Round and Ballot-by-Ballot election audits: a workbench for exploration
of risk-limiting audits.

# Installation

You can install the in-development version via:
```
git clone https://github.com/gwexploratoryaudits/r2b2.git
cd r2b2
pip install .
```

# Usage
R2B2 provides both a Python module for programatic use via its API, and a command-line interface.

Here are some command-line examples for getting interactive help and running audits:

    r2b2 --help
    r2b2 bulk --help
    r2b2 bulk -l "50 100" src/r2b2/tests/data/basic_contest.json brla 0.1 0.1
    r2b2 interactive -a minerva -r 0.1 -m 0.2 -v --contest-file src/r2b2/tests/data/basic_contest.json

# Documentation

The R2B2 API is documented at [r2b2.readthedocs.io](https://r2b2.readthedocs.io/).

# Development

See [Design Guide](https://github.com/gwexploratoryaudits/r2b2/blob/main/docs/design_guide.md)
for development standards and [Audit Design Guide](https://github.com/gwexploratoryaudits/r2b2/blob/docs/docs/audit_design_guide.md)
for information about adding an audit to the library.

To run all the tests run

```
tox
```

Note, to combine the coverage data from all the `tox` environments run:

**Windows**:
```
set PYTEST_ADDOPTS=--cov-append tox
```
**Other**:
```
PYTEST_ADDOPTS=--cov-append tox
```
