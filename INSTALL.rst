=========================================================
Pylens Installation
=========================================================

To install::

  $easy_install pylens

Or use the standard installation process, downloading the latest version from: http://pypi.python.org/pypi/pylens/

Alternatively, you can get the source from github and install it.

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


Development Notes
=========================================================

To generate and test the package, then upload it and the docs to PyPi run::
  
  python2 ./scripts/distribute.py [upload]
