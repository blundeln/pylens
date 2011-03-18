#
# Copyright (c) 2010-2011, Nick Blundell
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
# Author: Nick Blundell <blundeln@gmail.com>
# Organisation: www.nickblundell.org.uk
#
from nbdebug import d, breakpoint, set_indent_function, IN_DEBUG_MODE
from exceptions import *

def lens_assert(condition, message=None) :
  """
  Useful for assertion within lenses that should raise LensException, such that
  higher-level parsing may be resume, perhaps on an alternate branch.
  XXX: This might create confusing code though - perhaps best to thorw the exception
  XXX: Also we can loose the exceptions import.
  """
  if not condition :
    raise LensException(message)

class assert_raises:
  """A cleaner way to assert that an exception is thrown from some code."""
  
  def __init__(self, exception_class) :
    self.exception_class = exception_class
  
  def __enter__(self) :
    pass
  
  def __exit__(self, type, exception, traceback) :
    # Returning True means 'suppress exception', which we do if the exception of
    # of the type we expected.
    return isinstance(exception, self.exception_class)

  @staticmethod
  def TESTS() :
    d("Testing")
    
    # Assert the ZeroDivisionError is thrown 
    with assert_raises(ZeroDivisionError) :
      x = 1 / 0

    # My most beautiful test!
    with assert_raises(IndexError) :
      # The inner block will not suppress an exception it is not expecting.
      with assert_raises(ZeroDivisionError) :
        # This code raises a different exception than expected.
        x = []
        x[0] = 2



def debug_indent_function() :
  """
  Nicely indents the debug messages according to the hierarchy of lenses.
  """ 
  import inspect
  # Create a list of all function names in the trace.
  function_names = []

  # Prepend the callers location to the message.
  callerFrame = inspect.currentframe()
  while callerFrame :
    location = callerFrame.f_code.co_name
    function_names.append(location)
    callerFrame = callerFrame.f_back

  #indent = max(function_names.count("put"), function_names.count("get"))
  indent = 0
  for name in ["put", "get", "_put", "_get"] :
    indent += function_names.count(name)
  indent -= 1
  indent = max(0, indent)

  #print ">>>: " +str(function_names)
 
  return " "*indent

from nbdebug import set_indent_function
set_indent_function(debug_indent_function)


def auto_name_lenses(local_variables) :
  """Gives names to lenses based on their local variable names, which is
  useful for tracing parsing. Should be called with globals()/locals()"""
  for variable_name, obj in local_variables.iteritems() :
    if isinstance(obj, BaseLens) :
      obj.name = variable_name



