#
# Copyright (c) 2010, Nick Blundell
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Nick Blundell nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
#
#
# Author: Nick Blundell <blundeln [AT] gmail [DOT] com>
# Organisation: www.nickblundell.org.uk
# 
# Description:
# 
#

import sys

# Add required paths
sys.path.append("testing")

import unittest

from pylens import *
from tests import *
from examples.basic import *
from examples.advanced import *

from nbdebug import d

CLASS_TEST_FUNCTION = "TESTS"
FUNCTION_TEST_SUFFIX = "_test"

def get_tests() :
  
  # Automatically discover test routines.
  tests = {}
  for name, item in globals().iteritems() :
    # Add (long) test functions, or class unit tests
    if name.lower().endswith(FUNCTION_TEST_SUFFIX) :
      tests[name] = item
    elif hasattr(item, CLASS_TEST_FUNCTION):
      tests[item.__name__] = getattr(item, CLASS_TEST_FUNCTION)

  return tests


def test_set_up():
  """
  Ensure that all tests run with same global state, which some tests may alter.
  """
  GlobalSettings.check_consumption = True


def run_tests(test_mode, args) :
  
  all_tests = get_tests()
  
  if test_mode == "test" :
    filtered_tests = {}
    if not args :
      raise Exception("You must specify a series of tests")
    for test_name in args :
      # TODO: Allow omission of _test in specifying function tests.
      if test_name not in all_tests :
        raise Exception("There is no test called: %s" % test_name)
      filtered_tests[test_name] = all_tests[test_name]
  else :
    filtered_tests = all_tests
  
  test_suite = unittest.TestSuite()
  for name, test_function in filtered_tests.iteritems() :
    testcase = unittest.FunctionTestCase(test_function, description=name, setUp=test_set_up)
    test_suite.addTest(testcase)
 
  runner = unittest.TextTestRunner()
  test_result = runner.run(test_suite)
  
  # Useful to return an error code for repository commit hook.
  if not test_result.wasSuccessful() :
    sys.exit(1)


###########################
# Main.
###########################

def main() :
  # This can be useful for testing.
  pass

if __name__ == "__main__":
  import sys
  # Optionally run tests.
  
  if "commit_tests" in sys.argv :
    # Disable commit testing, for experimentation.
    pass #exit(0)

  if len(sys.argv) > 1 :
    print("="*50)
    print("Running tests")
    print("="*50)
    run_tests(sys.argv[1].lower(), sys.argv[2:])
  else :
    main()
