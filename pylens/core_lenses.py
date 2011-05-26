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


    # Position before we start consume chars.
    initial_position = concrete_input_reader.get_pos()
    
    # Parse as many chars as we can until the lens matches something.
    while not concrete_input_reader.is_fully_consumed() :
      try :
        start_state = get_rollbackables_state(concrete_input_reader)
        self.lenses[0].get(concrete_input_reader)
        
        # If we are not to include consumption of the lenes, roll back the state
        # after successfully getting the lens, since we do not want to include
        # consumption of the lens.
        if not self.include_lens :
          set_rollbackables_state(start_state, concrete_input_reader)
          
        break
      except LensException:
        pass

    parsed_chars = concrete_input_reader.get_consumed_string(initial_position) 

    if not parsed_chars :
      raise LensException("Expected to get at least one character!")
    
    return parsed_chars


  def _put(self, item, concrete_input_reader, current_container) :
    
    
    if not self.has_type() and has_value(item):
      raise Exception("As a nont-STORE lens, %s did not expect to be passed an item to PUT." % self)

    assert_msg(isinstance(item, str), "Expected to PUT a string.")

    # TODO: We should should check that the lens does not match within the
    # string if include_lens == False, or perhaps we just leave this to the user
    # to improve performance.

    # Ensure we consume the input if there is some.
    if concrete_input_reader :
      self.get(concrete_input_reader)

    return item


  @staticmethod
  def TESTS() :
    d("GET")
    lens = Group("("+Until(")", type=str) + ")", type=list)
    got = lens.get("(in the middle)")
    assert(got == ["in the middle"])
    
    d("PUT")
    output = lens.put(["monkey"])
    assert(output == "(monkey)")
   
    assert(lens.get(lens.put(["monkey"])) == ["monkey"])
    
    # XXX: Perhaps protect against this, or not?!
    #assert(lens.get(lens.put(["mon)key"])) == ["monkey"])





# XXX: Deprecated.
class CombineChars(Lens) :
  """
  Combines separate character tokens into strings in both directions.  This is
  extended by lenses such as Word and Literal.
  """
 
  # XXX: Should this be a lens at all, or something more fundamental, perhaps
  # relating to a collection? Since how do we handle if sub lens is optionally
  # a store or non-store? perhaps we can set the type of a lens to string?
  # e.g. Word(alpha) -> OneOrMore(AnyOf(alpha), type=str).
  # Hmmm, but then we still have a problem that combinators get merged.
  # XXX: Will need to think about this some more, since currently we cannot support
  # nesting of these (e.g. CombineChars(AnyOf(alpha), Literal("xyz")), which is why it
  # might be better if the string was fused at the edge of the API, as the types
  # are - but then sometimes we don't want this ????

  def __init__(self, lens, **kargs):
    super(CombineChars, self).__init__(**kargs)
    self.lens = lens

  def _get(self, concrete_reader) :
    """
    Gets the token from the sub lens, checking that it contains only a list of
    chars (no labelled tokens) or a single char before assembling them into a single
    string token.
    """

    token = self.lens.get(concrete_reader)
  
    # If token is None or if we are a non-store lens, regardless of the child
    # lens, return nothing here so that we save needless processing.
    if token == None or not self.store :
      return None

    # If the sub-lens GOT a string ...
    if isinstance(token, str) :
      # We will allow it through only if it is a single char or the empty string.
      lens_assert(len(token) <= 1, "Expected a single char string or empty.")
      return token

    lens_assert(token and isinstance(token, AbstractCollection), "Expected a collection of tokens")
    # Now we can assume we have a token collection.
    token_collection = token
    
    # Check no tokens are stored with labels - we just want a straight list of tokens.
    lens_assert(token_collection.dict.keys() == [None], "Cannot combine the output of a lens that stores tokens with labels.")
    
    # Build up the string from char tokens.
    string_value = ""
    for sub_token in token_collection.dict[None] :
      lens_assert(isinstance(sub_token, str) and len(sub_token) == 1, "Expect only single char tokens.")
      string_value += sub_token

    # XXX: Hmmm, is there any good reason why we cannot allow the empty string?
    #lens_assert(string_value, "Expected at least one char token.")

    return string_value

  def _put(self, abstract_token, concrete_input_reader) :
    
    # Expand the abstract_token into an ATR(ATC), then pass to lens.
    lens_assert(isinstance(abstract_token, str) and len(abstract_token) > 0, "Expected a non-empty string")

    token_collection = GenericCollection()
    for char in abstract_token :
      token_collection.add_token(char)

    # Return the output of the lens - using a reader in order for either combinator or simple lens to pick up as list of
    # chars or as a single char.
    return self.lens.put(AbstractTokenReader(token_collection), concrete_input_reader)

  @staticmethod
  def TESTSX() :
    d("GET")
    lens = CombineChars(AnyOf(alphas, store=True) + AnyOf(nums, store=True), store=True)
    concrete_reader = ConcreteInputReader("n6xxsf")
    token = lens.get(concrete_reader)
    assert(token == "n6" and concrete_reader.get_remaining() == "xxsf")

    d("PUT")
    output = lens.put("b3", "n6xxsf")
    d(output)
    assert(output == "b3")

    # CREATE
    output = lens.create("g9")
    assert(output == "g9")

    # For good measure - GET
    lens = CombineChars(OneOrMore(AnyOf(alphas, store=True)), store=True)
    concrete_reader = ConcreteInputReader("Nick1234")
    token = lens.get(concrete_reader)
    assert(token == "Nick" and concrete_reader.get_remaining() == "1234")

    # For good measure - PUT
    concrete_reader.reset()
    output = lens.put("Ed", concrete_reader)
    assert(output == "Ed" and concrete_reader.get_remaining() == "1234")


