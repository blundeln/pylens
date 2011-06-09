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
#   Stateful string reader classes (i.e. that can be rolled back for tentative parsing)
#

from debug import *
from exceptions import *
from util import *
from containers import *


class ConcreteInputReader(Rollbackable):
  """Stateful reader of the concrete input string."""

  def __init__(self, input_string):
    
    # If input_string is in fact a ConcreteInputReader, copy its state.
    if isinstance(input_string, self.__class__) :
      self.position = input_string.position
      self.string = input_string.string
    # Otherwise, initialise our state.
    else :
      assert(isinstance(input_string, str))
      self.position  = 0
      self.string    = input_string

  def reset(self) :
    self.set_pos(0)

  def _get_state(self, copy_state=True) :
    return self.get_pos()

  def _set_state(self, state, copy_state=True) :
    self.set_pos(state)

  def get_consumed_string(self, start_pos=0) :
    return self.string[start_pos:self.position]

  def get_pos(self):
    return self.position

  def set_pos(self, pos) :
    assert(isinstance(pos, int))
    self.position = pos

  def get_remaining(self) :
    """Return the text that remains to be parsed - useful for debugging."""
    return self.string[self.position:]

  def consume_string(self,length):
    """
    Consume a string of specified length from the input.
    """
    if self.position+length > len(self.string):
      raise EndOfStringException()
    start = self.position
    self.position += length
    return self.string[start:self.position]


  def consume_char(self):
    """
    Consume and return the next char from input.
    """
    if self.is_fully_consumed():
      raise EndOfStringException()
    char = self.string[self.position]
    self.position += 1
    return char


  def is_fully_consumed(self):
    """
    Return whether the string is fully consumed
    """
    return self.position >= len(self.string)


  def is_aligned_with(self, other) :
    """Check if this reader is aligned with another."""
    return self.position == other.position and self.string == other.string

  def __str__(self) :
    # Return a string representation of this reader, to help debugging.
    if self.is_fully_consumed() :
      return "END_OF_STRING"

    display_string = self.string[self.position:]
    return truncate(display_string)
  __repr__ = __str__

  @staticmethod
  def TESTS() :
    concrete_reader = ConcreteInputReader("ABCD")
    output = ""
    for i in range(0,2) :
      output += concrete_reader.consume_char()
    assert not concrete_reader.is_fully_consumed()
    assert concrete_reader.get_remaining() == "CD"
    assert concrete_reader.get_consumed_string(0) == "AB"
    
    for i in range(0,2) :
      output += concrete_reader.consume_char()
    assert output == "ABCD"
    assert concrete_reader.is_fully_consumed()
    
    concrete_reader = ConcreteInputReader("ABCD")

    # Now test with rollback.
    concrete_reader = ConcreteInputReader("ABCD")
    try :
      with automatic_rollback(concrete_reader):
        concrete_reader.consume_char()
        assert concrete_reader.get_remaining() == "BCD"
        raise LensException()
    except LensException:
      pass # Don't want to stop tests.

    assert concrete_reader.get_remaining() == "ABCD"

    # Test that clones share the string object, for efficiency.
    cloned_reader = ConcreteInputReader(concrete_reader)
    assert(cloned_reader.string is concrete_reader.string)
    assert(cloned_reader.is_aligned_with(concrete_reader))
    cloned_reader.position += 1
    assert(not cloned_reader.is_aligned_with(concrete_reader))


