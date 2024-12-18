This folder contains tests based on Python unittest. Tests are run from the root of the repo (pymdfu not pymdfu/pymdfu or pymdfu/pymdfu/tests)

To run all tests:
~~~~
\pymdfu>pytest
~~~~

To run a specific tests use the -k option of pytest to use a substring expression to mask tests.
For example to run all tests in test_mac_layers.py:
~~~~
\pymdfu>pytest -k test_mac_layers
~~~~
To run a specific test:
~~~~
\pymdfu>pytest -k test_socket_mac
~~~~

To get logging output when running tests use the --log-cli-level option.
Note that the -s option must also be added to get any printout from pytest
For example to turn on INFO level logging:
~~~~
\pymdfu>pytest --log-cli-level INFO -s
~~~~
