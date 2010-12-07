=========================================================
Pylens Installation
=========================================================

TODO: Use some python installation system, such as setuptools

Testing
=========================================================

Most objects declare their own tests, so the following will run all tests
cases::

  $ python testing/run_tests.py test

Or, to test specific things::

  $ python testing/run_tests.py test And
  $ python testing/run_tests.py test iface_test

For detailed debug log (using module nbdebug), run like this::

  $ NBDEBUG="" python testing/run_tests.py test iface_test

