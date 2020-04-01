# Overview

[![Documentation Status](https://readthedocs.org/projects/r2b2/badge/?version=latest)](https://r2b2.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/gwexploratoryaudits/r2b2.svg?branch=master)](https://travis-ci.org/gwexploratoryaudits/r2b2)
[![Requirements Status](https://requires.io/github/gwexploratoryaudits/r2b2/requirements.svg?branch=master)](https://requires.io/github/gwexploratoryaudits/r2b2/requirements/?branch=master)
[![Coverage Status](https://codecov.io/github/gwexploratoryaudits/r2b2/coverage.svg?branch=master)](https://codecov.io/github/gwexploratoryaudits/r2b2)
[![Commits since latest release](https://img.shields.io/github/commits-since/gwexploratoryaudits/r2b2/v0.1.0.svg)](https://github.com/gwexploratoryaudits/r2b2/compare/v0.1.0...master)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


Round-by-Round and Ballot-by-Ballot election audits: a workbench for exploration
of risk-limiting audits.

# Installation

```
pip install r2b2
```

You can also install the in-development version with:
```
pip install https://github.com/gwexploratoryaudits/r2b2/archive/master.zip
```

# Documentation

[r2b2.readthedocs.io](https://r2b2.readthedocs.io/)

# Development

See [Design Guide](https://github.com/gwexploratoryaudits/r2b2/blob/master/docs/design_guide.md)
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
