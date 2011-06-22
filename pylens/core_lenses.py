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
# Author: Nick Blundell <blundeln [AT] gmail [DOT] com>
# Organisation: www.nickblundell.org.uk
# 
#
import inspect
import sys
from exceptions import *
from containers import *
from readers import *
from util import *
from debug import *
from base_lenses import *


class Forward(Lens):
  """
  Allows forward declaration of a lens, which may be bound later, primarily to
  allow for lens recursion.  Based on the idea used in pyparsing, since we must
  define variables before we use them, unless we use some python interpreter
  pre-processing.
  """
  def __init__(self, recursion_limit=100, **kargs):
    super(Forward, self).__init__(**kargs)
    d("Creating")
    self.recursion_limit = recursion_limit
  
  def bind_lens(self, lens) :
    d("Binding to lens %s" % lens)
    assert_msg(len(self.lenses) == 0, "The lens cannot be re-bound.")
    self.set_sublens(lens)
  
  def _get(self, *args, **kargs) :
    assert_msg(len(self.lenses) == 1, "A lens has yet to be bound.")
    return self.lenses[0]._get(*args, **kargs)

  def _put(self, *args, **kargs) :
    assert_msg(len(self.lenses) == 1, "A lens has yet to be bound.")
    
    # Ensure the recursion limit is set before we start this.
    original_limit = sys.getrecursionlimit()
    if self.recursion_limit :
      sys.setrecursionlimit(self.recursion_limit)
    
    try :
      output = self.lenses[0]._put(*args, **kargs)
    except RuntimeError:
      raise InfiniteRecursionException("You will need to alter your grammar, perhaps changing the order of Or lens operands")
    finally :
      sys.setrecursionlimit(original_limit)
    
    return output


  # Use the lshift operator, as does pyparsing, since we cannot easily override (re-)assignment.
  def __lshift__(self, other) :
    assert_msg(isinstance(other, Lens), "Can bind only to a lens.")
    self.bind_lens(other)


  @staticmethod
  def TESTS():

    # TODO: Need to think about semantics of this and how it will work with groups.
    d("GET")
    lens = Forward()
    # Now define the lens (must use '<<' rather than '=', since cannot easily
    # override '=').
    lens << "[" + (AnyOf(alphas, type=str) | lens) + "]"
    
    # Ensure the lens is enclosed in a container lens.
    lens = Group(lens, type=list)
    
    got = lens.get("[[[h]]]")
    assert(got == ["h"])
    
    d("PUT")
    got[0] = "p"
    output = lens.put(got)
    assert(output == "[[[p]]]")

    # Note that this lens results in infinite recursion upon CREATE.
    d("CREATE")
    output = lens.put(["k"])
    assert(output == "[k]")
    
    # If we alter the grammar slightly, we will get an infinite recursion error,
    # since the lens could recurse to an infinite depth before considering the
    # AnyOf() lens.
    lens = Forward() 
    lens << "[" + (lens | AnyOf(alphas, type=str)) + "]"
    lens = Group(lens, type=list)
    with assert_raises(InfiniteRecursionException) :
      output = lens.put(["k"])
    

class Until(Lens) :
  """
  Match anything up until the specified lens.  This is useful for lazy parsing,
  but not the be overused (e.g. chaining can be bad: Until("X") + Until("Y")!).
  
  # TODO: Could parse lens but not include in stored string.
  """
  
  def __init__(self, lens, include_lens=False, **kargs):
    """
    Arguments:
      include_lens - Set to true if the specified lens should also be consumed.
    """
    super(Until, self).__init__(**kargs)
    self.set_sublens(lens)
    self.include_lens = include_lens

  def _get(self, concrete_input_reader, current_container) :

    # Remember the input position before we start to consume chars.
    initial_position = concrete_input_reader.get_pos()
    
    stopping_lens = self.lenses[0]
   
    while True :
      start_state = get_rollbackables_state(concrete_input_reader)
      try :
        stopping_lens.get(concrete_input_reader)

        # If we are not to include consumption of the lenes, roll back the state
        # after successfully getting the lens, since we do not want to include
        # consumption of the lens.
        if not self.include_lens :
          d("Rollbacked from %s" % get_rollbackables_state(concrete_input_reader))
          set_rollbackables_state(start_state, concrete_input_reader)
          d("Rollbacked to %s" % get_rollbackables_state(concrete_input_reader))
        else :
          pass

        break
      
      except LensException :
        # We have not reached the stopping lens in input yet, so we rollback and then carry on.
        d("stopping_lens failed soi continuing.")
        set_rollbackables_state(start_state, concrete_input_reader)
      
      # Advance the input reader by one char - this will form part of our lens' GOTen string.
      try :
        concrete_input_reader.consume_char()
      except EndOfStringException:
        # Break if we reach the end of the input.
        break

    parsed_chars = concrete_input_reader.get_consumed_string(initial_position) 

    if not parsed_chars :
      raise LensException("Expected to get at least one character!")
    
    return parsed_chars


  def _put(self, item, concrete_input_reader, current_container) :
    
    if self.has_type() :
      if not isinstance(item, str) and len(item) > 0:
        raise Exception("Expected to be passed a string of length at least one character, not %s." % item)
      
      # Consume input.
      if concrete_input_reader :
        self.get(concrete_input_reader)
      output = item
    else :
      if has_value(item):
        raise LensException("As a non-STORE lens, %s did not expect to be passed an item %s to PUT." % (self, item))
      
      # Use output from input, or fail if we have no concrete input.
      if concrete_input_reader :
        output = self.get(concrete_input_reader)
      else :
        raise NoDefaultException("Cannot CREATE: a default should have been set on lens %s, or an outer lens." % self)

    return output


  @staticmethod
  def TESTS() :
    d("GET")
    lens = Group("("+Until(")", type=str) + ")", type=list)
    got = lens.get("(in the middle)")
    assert(got == ["in the middle"])

    d("PUT")
    output = lens.put(["monkey"])
    assert(output == "(monkey)")
   
    test_description("Try with include_lens=True")
    assert(lens.get(lens.put(["monkey"])) == ["monkey"])
    lens = Group("("+Until(")", type=str, include_lens=True), type=list)
    got = lens.get("(in the middle)")
    assert(got == ["in the middle)"])

    # XXX: Perhaps protect against this, or perhaps leave to lens user to worry about?!
    #assert(lens.get(lens.put(["mon)key"])) == ["monkey"])
