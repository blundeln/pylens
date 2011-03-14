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

# TODO: Allow all unit testing to be performed alone.
# Different testing modes.
UNIT_TESTS = "unit_tests"
LONG_TESTS = "long_tests"
ALL_TESTS = "all"

# Import everything in the library
from pylens import *

# And import the longer, integrated tests.
from long_tests import *


def run_tests(args) :
  unit_tests(args)

def unit_tests(args=None) :
  
  import unittest

  # Automatically discover test routines.
  TESTS = {}
  for name, item in globals().iteritems() :
    # Add (long) test functions, or class unit tests
    if name.lower().endswith("_test") :
      TESTS[name] = item
    elif hasattr(item, "TESTS"):
      TESTS[item.__name__] = item.TESTS

  # Determine if a specific test was specified to be run.
  test_name = args[-1]
  if test_name == "test" :
    test_name = None

  # XXX: Whilst experimenting. 
  if not test_name :
    exit(0)

  if test_name and test_name not in TESTS :
    raise Exception("There is no test called: %s" % test_name)



  test_suite = unittest.TestSuite()
  for name, test_function in TESTS.iteritems() :
    if test_name and (name != test_name) :
      continue
    testcase = unittest.FunctionTestCase(test_function, description=name)
    test_suite.addTest(testcase)
  
  runner = unittest.TextTestRunner()
  test_result = runner.run(test_suite)
  if not test_result.wasSuccessful() :
    sys.exit(1)



###########################
# Main.
#

def main() :
  # This can be useful for testing.
  pass

if __name__ == "__main__":
  import sys
  # Optionally run tests.
  if len(sys.argv) > 1 :
    print("="*50)
    print("Running tests")
    print("="*50)
    run_tests(sys.argv)
  else :
    main()
