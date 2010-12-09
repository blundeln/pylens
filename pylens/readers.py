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
from nbdebug import d, breakpoint, set_indent_function, IN_DEBUG_MODE
from excepts import *
from util import *
from token_collections import *

class Reader :
  """Interface of a Reader with position state, so it can be rolled back"""
  def get_position_state(self) :
    raise NotImplementedError()

  def set_position_state(self, state) :
    raise NotImplementedError()

  def is_fully_consumed(self):
    raise NotImplementedError()


class ConcreteInputReader(Reader):
  """Stateful reader of the concrete input string."""

  def __init__(self, string):
    self.position  = 0
    self.string       = string

  def reset(self) :
    self.set_pos(0)

  def get_position_state(self) :
    return self.get_pos()

  def set_position_state(self, state) :
    self.set_pos(state)

  def get_consumed_string(self, start_pos) :
    return self.string[start_pos:self.position]

  def get_pos(self):
    return self.position

  def set_pos(self, pos) :
    self.position = pos

  def get_remaining(self) :
    """Return the text that remains to be parsed - useful for debugging."""
    return self.string[self.position:]

  def get_string(self,length):
    """
    Consume the next string of specified length from the input.
    """
    if self.position+length > len(self.string):
      raise EndOfStringException()
    start = self.position
    self.position += length
    return self.string[start:self.position]


  def get_next_char(self):
    """
    Consume and return the next char from input.
    """
    if self.position == len(self.string):
      raise EndOfStringException()
    char = self.string[self.position]
    self.position += 1
    return char

  def is_fully_consumed(self):
    """
    Return whether the string was fully consumed
    """
    return self.get_remaining() == ""

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
      output += concrete_reader.get_next_char()
    assert not concrete_reader.is_fully_consumed()
    assert concrete_reader.get_remaining() == "CD"
    assert concrete_reader.get_consumed_string(0) == "AB"
    for i in range(0,2) :
      output += concrete_reader.get_next_char()
    assert output == "ABCD"
    assert concrete_reader.is_fully_consumed()


class AbstractTokenReader(Reader):
  """Stateful reader of an abstract token collection, to enable un-parsing of the tokens."""
 
  # Special key for storing position state of the label token.
  LABEL_TOKEN = "__LABEL_TOKEN__"

  # Alias counting list indicies
  COUNT = 0
  MAX_COUNT = 1
  
  def __init__(self, tokens) :

    # Normalise tokens into a AbstractCollection, such that a plain list or dict may be passed
    self.token_collection = TokenTypeFactory.normalise_incoming_token(tokens)
    
    # Set up the initial position state.
    self.reset()

  def reset(self) :
    """Resets the position state of the reader."""
    self.position_state = {}
    for label in self.token_collection.get_labels() :
      # We also store alongside the count the max number of tokens in the labelled lists.
      self.position_state[label]  = [0, self.token_collection.get_no_tokens(label=label)]
    
    # And so we can track the label token...
    label_token = self.token_collection.get_label_token()
    if label_token :
      self.position_state[self.LABEL_TOKEN] = [0, 1]

  def get_position_state(self) :
    # Note: This must return a copy of the structure, so that modification of one does not affect the other.
    import copy
    return copy.deepcopy(self.position_state)

  def set_position_state(self, position_state) :
    # Note: this must set a copy of the structure - otherwise a frozen state could still be changed if later set.
    # This one caught me out ;)
    import copy
    self.position_state = copy.deepcopy(position_state)

  def has_more_tokens(self) :
    """Checks if any tokens remain at all."""
    for label in self.position_state :
      if self.has_more_tokens_with_label(label = label) :
        return True
    return False
  
  def has_more_tokens_with_label(self, label) :
    """Note, we also treat None as a label."""
    if label not in self.position_state :
      return False
    return self.position_state[label][self.COUNT] < self.position_state[label][self.MAX_COUNT]

  def get_next_token(self, label=None) :
    if not self.has_more_tokens_with_label(label=label) :
      raise LensException("No more tokens left - all have been consumed in '%s'" % label)

    token_index = self.position_state[label][self.COUNT]
    
    # Handle special case of getting the label token.
    if label == self.LABEL_TOKEN :
      next_token = self.token_collection.get_label_token()
    else :
      next_token = self.token_collection.get_token(token_index, label=label) 
    
    # Increment position state.
    self.position_state[label][self.COUNT] += 1

    return next_token

  def __str__(self) :
    return pformat(self.position_state)
  __repr__ = __str__

  @staticmethod
  def TESTS() :
    token_collection = GenericCollection(["snake", "cow"])
    token_collection.add_token("baboon", label="monkeys")
    token_collection.set_label_token("chimp")
    atr = AbstractTokenReader(token_collection)
    assert atr.get_next_token() == "snake"
    assert atr.get_next_token() == "cow"
    try: 
      atr.get_next_token(); assert False, "This should fail - we should not get here!"
    except LensException:
      pass

    position_state = atr.get_position_state()
    assert atr.get_next_token(label="monkeys") == "baboon"
    assert atr.get_next_token(label=AbstractTokenReader.LABEL_TOKEN) == "chimp"
    try: atr.get_next_token(label="monkeys"); assert False, "This should fail - we should not get here!"
    except LensException: pass

    # Test setting previous state.
    atr.set_position_state(position_state)
    assert atr.get_next_token(label="monkeys") == "baboon"
    assert atr.get_next_token(label=AbstractTokenReader.LABEL_TOKEN) == "chimp"
    try: atr.get_next_token(label="monkeys"); assert False, "This should fail - we should not get here!"
    except LensException: pass
  
    # Again, test setting previous state, making sure stored state was not changed.
    atr.set_position_state(position_state)
    assert atr.get_next_token(label="monkeys") == "baboon"
    assert atr.get_next_token(label=AbstractTokenReader.LABEL_TOKEN) == "chimp"
    try: atr.get_next_token(label="monkeys"); assert False, "This should fail - we should not get here!"
    except LensException: pass

    # Check collection casting working
    atr = AbstractTokenReader(["x", "y", "z"])
    assert atr.get_next_token() == "x"
    assert atr.get_next_token() == "y"

    # And same for dict
    atr = AbstractTokenReader({"name":"nick", "gender":"male"})
    d(atr)
    assert atr.get_next_token(label="name") == "nick"
    try: atr.get_next_token(label="name"); assert False, "This should fail - we should not get here!"
    except LensException: pass
    
    # And for object
    class Person:
      def __init__(self, name, gender, age) :
        self.name, self.gender, self.age = name, gender, age

    person = Person("nick", "male", 30)
    atr = AbstractTokenReader(person)
    d(atr)
    assert atr.get_next_token(label="name") == "nick"
    assert atr.get_next_token(label="age") == 30
    try: atr.get_next_token(label="name"); assert False, "This should fail - we should not get here!"
    except LensException: pass



def get_readers_state(*readers) :
  """Handy function to get the state of multiple readers, conviently ignoring those with value None."""
  # Note: readers must be in same order for get and set.
  readers_state = []
  for reader in readers :
    if isinstance(reader, Reader) :
      readers_state.append(reader.get_position_state())

  #d(str(readers_state))
  return readers_state

def set_readers_state(new_readers_state, *readers) :
  state_index = 0
  #d(str(new_readers_state) + " " + str(readers))
  for reader in readers:
    if isinstance(reader, Reader) :
      reader.set_position_state(new_readers_state[state_index])
      state_index += 1


# Allows rollback of reader state using 'with' statement
class reader_rollback:
  
  def __init__(self, *readers) :
    # Store the readers. Note, for convenience, allow readers to be None (i.e. store only Reader instances)
    self.readers = readers
  
  def __enter__(self) :
    # Store the start state of each reader.
    self.start_state = get_readers_state(*self.readers)
  
  def __exit__(self, type, value, traceback) :
    # If a LensException is thrown, revert all of the readers.
    if type and issubclass(type, LensException) :
      set_readers_state(self.start_state, *self.readers)
      d("Rolled back readers to: %s." % str(self.readers))
    
    # Note, by not returning True, we do not supress the exception.


  @staticmethod
  def TESTS() :
    abstract_token_reader = AbstractTokenReader(["beans", "eggs", "sausages"])
    concrete_input_reader = ConcreteInputReader("hello world")
    
    # No exception
    with reader_rollback(abstract_token_reader, concrete_input_reader):
      assert abstract_token_reader.get_next_token() == "beans"
      assert concrete_input_reader.get_next_char() == "h"
    
    assert abstract_token_reader.get_next_token() == "eggs"
    assert concrete_input_reader.get_next_char() == "e"

    try :
      with reader_rollback(abstract_token_reader, concrete_input_reader):
        d(abstract_token_reader.get_next_token()) # This will get 'sausages'
        d(concrete_input_reader.get_next_char())  # This will get 'l'
        raise LensException("Testing rollback")
    except LensException:
      pass # Don't wish to stop test run.

    # The exception in the with statement should cause readers to rollback
    assert abstract_token_reader.get_next_token() == "sausages"
    assert concrete_input_reader.get_next_char() == "l"
