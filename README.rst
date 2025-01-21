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
* Download and extract interlocking goods scripts from Afesta vcz archives
  (supports extracting scripts in both Vorze CSV and Funscript formats)

Note: 8K downloads are not currently supported, as 4D Media Player only downloads
the 4K version for 8K videos. Interlocking goods vcz download and extraction are
supported for 8K videos downloaded via the Afesta website.


Requirements
------------

* Python 3.10+
* Valid Afesta account


Installation
------------

You can install *Afesta Tools* via pip_ from PyPI_:

.. code:: console

   $ pip install afesta-tools


Usage
-----

Login to Afesta via CLI (not required on Windows if 4D Media Player is
installed and logged into Afesta):

.. code:: console

    $ afesta login
    Afesta username: username
    Afesta password:

List purchased videos which can be downloaded:

.. code:: console

    $ afesta list
    PRVR-050-Takumi: 【4K匠】指名No. 1泡姫・涼森れむの中出しソ...
    3DSVR-1393: 【8KHQ】【紗倉まな8K解禁】妻に捨てられ、残...
    ...

    $ afesta list -d
    PRVR-050-Takumi:
      【4K匠】指名No. 1泡姫・涼森れむの中出しソープ濃厚ご奉仕SEX！
      Parts: 3
      Actresses: 涼森れむ
      Genres: 女優
      Release date: 01/29/21 10:00:00 JST
      Duration: 1:16:26
    ...

    $ afesta list -l en
    PRVR-050-Takumi: [4K Takumi] Hardcore Cre...
    3DSVR-1393: 8KHQ] [8K Liberation of ...
    ...

    $ afesta list -d -l en
    PRVR-050-Takumi:
      [4K Takumi] Hardcore Creampie with the Best Girl in the Brothel, starring Remu Suzumori
      Parts: 3
      Actresses: Remu Suzumori
      Genres: AV Actresses
      Release date: 01/29/21 10:00:00 JST
      Duration: 1:16:26
    ...

Download videos:

.. code:: console

    $ afesta dl PRVR-050                                                                                                           ⏎
    Downloading PRVR-050-Takumi: 【4K匠】指名No. 1泡姫・涼森れむの中出しソ... (3 parts):   0%|           | 97.7M/19.6G [00:15<50:15, 6.48MB/s]

    $ tree .
    .
    ├── PRVR-050-Takumi-R1_sbs.mp4
    ├── PRVR-050-Takumi-R2_sbs.mp4
    └── PRVR-050-Takumi-R3_sbs.mp4

Download vcz archives for Afesta video files:

.. code:: console

    $ afesta dl-vcz PRVR-050-Takumi-*.mp4
    100%|██████████████████████████████████████████████████| 430k/430k [00:00<00:00, 740kB/s]
    100%|██████████████████████████████████████████████████| 509k/509k [00:00<00:00, 852kB/s]
    100%|██████████████████████████████████████████████████| 454k/454k [00:00<00:00, 752kB/s]

    $ tree .
    .
    ├── PRVR-050-Takumi-R1_sbs.mp4
    ├── PRVR-050-Takumi-R1_sbs.vcz
    ├── PRVR-050-Takumi-R2_sbs.mp4
    ├── PRVR-050-Takumi-R2_sbs.vcz
    ├── PRVR-050-Takumi-R3_sbs.mp4
    └── PRVR-050-Takumi-R3_sbs.vcz

Extract CSV scripts from vcz archives:

.. code:: console

    $ afesta extract-script --format csv --format funscript PRVR-050-Takumi-*.vcz
    Extracted PRVR-050-Takumi-R1_sbs_cyclone.csv
    Extracted PRVR-050-Takumi-R1_sbs.funscript
    Extracted PRVR-050-Takumi-R1_sbs_piston.csv
    Extracted PRVR-050-Takumi-R1_sbs_onarhythm.csv
    ...

    $ tree .
    .
    ├── PRVR-050-Takumi-R1_sbs.funscript
    ├── PRVR-050-Takumi-R1_sbs.mp4
    ├── PRVR-050-Takumi-R1_sbs.vcz
    ├── PRVR-050-Takumi-R1_sbs_cyclone.csv
    ├── PRVR-050-Takumi-R1_sbs_onarhythm.csv
    ├── PRVR-050-Takumi-R1_sbs_piston.csv
    ├── PRVR-050-Takumi-R2_sbs.funscript
    ├── PRVR-050-Takumi-R2_sbs.mp4
    ├── PRVR-050-Takumi-R2_sbs.vcz
    ├── PRVR-050-Takumi-R2_sbs_cyclone.csv
    ├── PRVR-050-Takumi-R2_sbs_onarhythm.csv
    ├── PRVR-050-Takumi-R2_sbs_piston.csv
    ├── PRVR-050-Takumi-R3_sbs.funscript
    ├── PRVR-050-Takumi-R3_sbs.mp4
    ├── PRVR-050-Takumi-R3_sbs.vcz
    ├── PRVR-050-Takumi-R3_sbs_cyclone.csv
    ├── PRVR-050-Takumi-R3_sbs_onarhythm.csv
    └── PRVR-050-Takumi-R3_sbs_piston.csv

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
