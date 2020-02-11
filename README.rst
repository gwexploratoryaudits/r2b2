========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |requires|
        | |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|
.. |docs| image:: https://readthedocs.org/projects/r2b2/badge/?style=flat
    :target: https://readthedocs.org/projects/r2b2
    :alt: Documentation Status

.. |travis| image:: https://api.travis-ci.org/gwexploratoryaudits/r2b2.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/gwexploratoryaudits/r2b2

.. |requires| image:: https://requires.io/github/gwexploratoryaudits/r2b2/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/gwexploratoryaudits/r2b2/requirements/?branch=master

.. |codecov| image:: https://codecov.io/github/gwexploratoryaudits/r2b2/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/gwexploratoryaudits/r2b2

.. |version| image:: https://img.shields.io/pypi/v/r2b2.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/r2b2

.. |wheel| image:: https://img.shields.io/pypi/wheel/r2b2.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/r2b2

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/r2b2.svg
    :alt: Supported versions
    :target: https://pypi.org/project/r2b2

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/r2b2.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/r2b2

.. |commits-since| image:: https://img.shields.io/github/commits-since/gwexploratoryaudits/r2b2/v0.1.0.svg
    :alt: Commits since latest release
    :target: https://github.com/gwexploratoryaudits/r2b2/compare/v0.1.0...master



.. end-badges

Round-by-Round and Ballot-by-Ballot election audits: a workbench for exploration of risk-limiting audits

* Free software: MIT license

Installation
============

::

    pip install r2b2

You can also install the in-development version with::

    pip install https://github.com/gwexploratoryaudits/r2b2/archive/master.zip


Documentation
=============


https://r2b2.readthedocs.io/


Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
