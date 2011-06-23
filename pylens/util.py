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
# Author: Nick Blundell <blundeln [AT] gmail [DOT] com>
# Organisation: www.nickblundell.org.uk
# 
# Description:
#   Utilities of global use.
#
import copy
from debug import *


class Properties(object):
  """
  A useful class for holding properties (e.g. meta data or lens options), which
  uses __getattr__ to save us from always asking if it has a particular attribute.
  """
  def __init__(self, **kargs) :
    self.__dict__.update(kargs)

  def __getattr__(self, name) :
    # This is important, since obj.__dict__ would equal None!
    if name.startswith("__") :
      return super(object, self).__getattr__(name)

    if name in self.__dict__ :
      return self.__dict__[name]
    else :
      return None

  def copy(self) :
    return copy.copy(self)

  def unwrap(self) :
    return self.__dict__

  def clear(self) :
    """Useful in test cases."""
    self.__dict__ = {}

  def __str__(self) :
    return str(self.__dict__)
  __repr__ = __str__

  @staticmethod
  def TESTS() :
    d("Testing")
    properties = Properties(food="cheese")
    assert(properties.food == "cheese")
    properties.something = [1,2,3]
    assert(properties.something == [1,2,3])
    assert(properties.nothing == None)


def get_class_attr(obj, name, default=None):
  """Specifically get an attribute of an object's class."""
  return getattr(obj.__class__, name, default)

def get_instance_attr(obj, name, default=None) :
  """
  Specifically get an attribute of an instance (i.e. do not fall back on a
  class attribute with the same name, as does getattr).
  """
  class_value = get_class_attr(obj, name)
  obj_value = getattr(obj, name, default)
  
  # If there was no instance attribute by that name, getattr will return the
  # class_value if it exists, which we do not want.
  if has_value(class_value) and obj_value is class_value :
    return default
  
  return obj_value


def escape_for_display(s) :
  """Substitute certain chars to assist debug traces."""
  if len(s) == 0 :
    return "[EMPTY]"
  return s.replace("\n","[NL]").replace("\t","[TAB]") #.replace(" ","[SP]") # Escape newlines so not to confuse debug output.

def truncate(s, max_len=10) :
  """Truncates a long string so is suitable for display."""
  MAX_LEN = max_len
  display_string = escape_for_display(s)
  if len(s) == 0 :
    return display_string # Display empty string token.
  if len(s) > MAX_LEN :
    display_string = display_string[0:MAX_LEN] + "..."
  return display_string

def range_truncate(s, max_len=8) :
  """Truncate a string to assist debug traces."""
  if len(s) > max_len :
    return s[0:2] + "..." + s[-2:]
  return s


def has_value(var) :
  """To avoid possible comparison bugs with empty values vs None."""
  return var != None


#
# TESTS
#

def attr_test():
  test_description("Test behaviour of getattr when there is ambiguity over instance and class attributes")
  class A:
    a1 = 2
  a = A()

  assert_equal(getattr(a,"a1",None), 2)
  assert_equal(get_instance_attr(a,"a1",None), None)
  a.a1 = 5
  assert_equal(getattr(a,"a1",None), 5)
  assert_equal(get_instance_attr(a,"a1",None), 5)
  assert_equal(get_class_attr(a,"a1",None), 2)



