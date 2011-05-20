=========================================================
Pylens Installation
=========================================================

TODO: Use some python installation system, such as setuptools

Testing
=========================================================

Most objects declare their own tests, so the following will run all tests
cases::

  $ python scripts/run_tests.py all_tests

Or, to test specific things::

  $ python scripts/run_tests.py test And AnyOf
  $ python scripts/run_tests.py test iface_test

For detailed debug log (using module nbdebug), run like this::

  $ NBDEBUG="" python scripts/run_tests.py test iface_test
