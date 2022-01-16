Afesta Tools
============

|PyPI| |Status| |Python Version| |License|

|Read the Docs| |Tests| |Codecov|

|pre-commit| |Black|

Library and tools for AFesta.tv

.. |PyPI| image:: https://img.shields.io/pypi/v/afesta-tools.svg
   :target: https://pypi.org/project/afesta-tools/
   :alt: PyPI
.. |Status| image:: https://img.shields.io/pypi/status/afesta-tools.svg
   :target: https://pypi.org/project/afesta-tools/
   :alt: Status
.. |Python Version| image:: https://img.shields.io/pypi/pyversions/afesta-tools
   :target: https://pypi.org/project/afesta-tools
   :alt: Python Version
.. |License| image:: https://img.shields.io/pypi/l/afesta-tools
   :target: https://opensource.org/licenses/MIT
   :alt: License
.. |Read the Docs| image:: https://img.shields.io/readthedocs/afesta-tools/latest.svg?label=Read%20the%20Docs
   :target: https://afesta-tools.readthedocs.io/
   :alt: Read the documentation at https://afesta-tools.readthedocs.io/
.. |Tests| image:: https://github.com/bhrevol/afesta-tools/workflows/Tests/badge.svg
   :target: https://github.com/bhrevol/afesta-tools/actions?workflow=Tests
   :alt: Tests
.. |Codecov| image:: https://codecov.io/gh/bhrevol/afesta-tools/branch/main/graph/badge.svg
   :target: https://app.codecov.io/gh/bhrevol/afesta-tools
   :alt: Codecov
.. |pre-commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
.. |Black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Black


Features
--------

* Login to Afesta/LPEG API and register as a new player/client
* Re-use existing 4D Media Player installation + login credentials when
  available (Windows only)
* Download Afesta videos via CLI (requires valid account and appropriate
  purchases/permissions)


Requirements
------------

* Python 3.8+
* Valid Afesta account


Installation
------------

You can install *Afesta Tools* via pip_ from PyPI_:

.. code:: console

   $ pip install afesta-tools


Usage
-----

Login to Afesta via CLI:

.. code:: console

    $ afesta login
    Afesta username: username
    Afesta password:

Download videos:

.. code:: console

    $ afesta dl m1234-0000 m1234-0000_1 m1234-0000_2 m1234-0000_3

Please see the `Command-line Reference <Usage_>`_ for details.


Contributing
------------

Contributions are very welcome.
To learn more, see the `Contributor Guide`_.


License
-------

Distributed under the terms of the `MIT license`_,
*Afesta Tools* is free and open source software.


Issues
------

If you encounter any problems,
please `file an issue`_ along with a detailed description.


Credits
-------

This project was generated from `@cjolowicz`_'s `Hypermodern Python Cookiecutter`_ template.

.. _@cjolowicz: https://github.com/cjolowicz
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _MIT license: https://opensource.org/licenses/MIT
.. _PyPI: https://pypi.org/
.. _Hypermodern Python Cookiecutter: https://github.com/cjolowicz/cookiecutter-hypermodern-python
.. _file an issue: https://github.com/bhrevol/afesta-tools/issues
.. _pip: https://pip.pypa.io/
.. github-only
.. _Contributor Guide: https://afesta-tools.readthedocs.io/en/latest/contributing.html
.. _Usage: https://afesta-tools.readthedocs.io/en/latest/usage.html
