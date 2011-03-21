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
from nbdebug import d, breakpoint, set_indent_function, IN_DEBUG_MODE
from exceptions import *
from containers import *
from readers import *
from util import *
from debug import *
from base_lenses import *

#################################################
# Old stuff - for refactoring.
#################################################


# XXX: Filler until we rmeove refs to it
class CombinatorLens: pass



class OneOrMore(CombinatorLens) :
  """Allows a lens to be repeated, indefinitely."""
  # TODO: Adapt this to be the lens Multiple, where min and max can be specified, then
  # OneOrMore and perhaps ZeroOrMore can simply specialisations.

  def __init__(self, lens, min_items=1, max_items=None, **kargs):
    
    super(OneOrMore, self).__init__(**kargs)
    # Store the lens that we will repeat
    # TODO: Can we perhaps normalise sub-lens setting in the BaseClass so we don't forget to pre-process lenses in classes such as this.
    self.lens = self._preprocess_lens(lens)

    # Connect the lens to itself, since it may follow or proceed itself.
    for last_lens in self.lens.get_last_lenses() :
      for first_lens in self.lens.get_first_lenses() :
        # Lens may connect to itself here (e.g. OM(Literal("A"))
        last_lens._connect_to(first_lens)

    # TODO: Make use if these bounds are set
    assert(min_items >= 1)
    self.min_items, self.max_items = min_items, max_items
  
  def _get(self, concrete_input_reader) :
    
    # Create an apporiate collection for the type of this lens (e.g may be a simple list).
    token_collection = self._create_collection()
    # Consume as many as possible, until GET fails or until we have min items should the lens consume
    # none of the input string.
    no_GOT = 0
    while True:
      try :
        start_position = concrete_input_reader.get_position_state()
        token = self.lens.get(concrete_input_reader, postprocess_token=False)
        self._store_token(token, self.lens, token_collection)
        no_GOT += 1
        # If the lens did not consume from the concrete input and we now have min items, break out.
        if start_position == concrete_input_reader.get_position_state() and no_GOT >= self.min_items :
          d("Got minimum items, so breaking out to avoid infinite loop")
          break
      except LensException:
        break
    
    # TODO: Bounds checking.
    lens_assert(no_GOT > 0, "Must GET at least one.")
    return token_collection


  def _put(self, abstract_data, concrete_input_reader) :
    
    # Algorithm Outline
    #  PUT:
    #   - PUT as many items as possible
    #   - CREATE remaining items, if any
    #   - GET (i.e. consume) any remaining items from input
    #  CREATE:
    #   - CREATE items, if any
    #  BUT:
    #   - Suppose the lens (or its sub-lenses) does not consume tokens, we could CREATE indefinitely, so we
    #     check for token consumption with each iteration.

    # We can accept the current abstract reader or a GenericCollection.
    if isinstance(abstract_data, AbstractTokenReader) :
      abstract_token_reader = abstract_data
    elif isinstance(abstract_data, AbstractCollection) :
      abstract_token_reader = AbstractTokenReader(abstract_data)
    else :
      raise LensException("Expected either an AbstractTokenReader or GenericCollection")

    output = ""
    num_output = 0

    # Try to PUT some
    if concrete_input_reader :
      while True :
        try :
          output += self.lens.put(abstract_token_reader, concrete_input_reader)
          num_output += 1
        except LensException:
          break

    # Try to CREATE some, being careful to monitor the non-consumption of tokens.
    while True :
      try :
        # Store the start state, so we can track it the lens consumed any tokens,
        # to avoid an infinite loop.
        start_state = abstract_token_reader.get_position_state()
        lens_output = self.lens.create(abstract_token_reader)
        end_state = abstract_token_reader.get_position_state()

        # If no tokens were consumed and we already have >= min_items, break out.
        if end_state == start_state and num_output >= self.min_items:
          break
        
        output += lens_output
        num_output += 1
      except LensException:
        break

    # Try to GET some - so if we now have fewer abstract tokens than were
    # represented in concrete input.
    if concrete_input_reader :
      while True :
        try :
          self.lens.get(concrete_input_reader)
        except LensException:
          break

    lens_assert(num_output >= self.min_items, "Should process at least %d items." % self.min_items) 

    return output

  # TODO: Perhaps only override these for special cases, since most lenses will do the same.
  def get_first_lenses(self):
    return self.lens.get_first_lenses()
  def get_last_lenses(self):
    return self.lens.get_last_lenses()

  @staticmethod
  def TESTSX() :
    d("GET")
    lens = OneOrMore(AnyOf(alphanums, store=True))
    token = lens.get("m1x3_p6", check_fully_consumed=False)
    d(token)
    assert_match(str(token), "...['m', '1', 'x', '3']...")
    try : lens.get("_m1x3_p6", check_fully_consumed=False); assert False, "This should fail - we should not get here!"
    except: pass

    d("PUT")
    concrete_reader = ConcreteInputReader("m1x3_p6")
    output = lens.put(["r","o","b","0","t"], concrete_reader)
    d(output)
    assert concrete_reader.get_consumed_string(0) == "m1x3"
    assert output == "rob0t"
    
    concrete_reader = ConcreteInputReader("m1x3_p6")
    output = lens.put(["N", "B"], concrete_reader)
    assert concrete_reader.get_consumed_string(0) == "m1x3"
    assert output == "NB"

    d("CREATE")
    output = lens.create(["N", "B"])
    assert output == "NB"

    # Test for infinite create problem.
    lens = OneOrMore(AnyOf(alphanums, store=False, default="q"))
    output = lens.put([], "m1x3_p6")
    assert output == "m1x3" # Happy to put back what was there.
    output = lens.put([], "_p6")
    assert output == "q" # We at least want to create one, so use default.
    
    d("Type testing")
    lens = OneOrMore(AnyOf(alphanums, store=True), type=list)
    token = lens.get("m1x3_p6", check_fully_consumed=False)
    d(token)
    assert isinstance(token, list)
    output = lens.put(['x','y','z'], "m1x3_p6")
    d(output)

    # Check we avoid infinite loop
    d("Empty CREATE test")
    lens = OneOrMore(Empty())
    d("Do we loop indefinitely here?...")
    output = lens.create([])
    d("No, we do not, which is good :)")

    d("Empty GET test")
    d("Do we loop indefinitely here?...")
    lens.get("abc", check_fully_consumed=False)
    d("No, we do not, which is good :)")





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


class Until(Lens) :
  """
  Match anything up until the specified lens.  This is useful for lazy parsing,
  but not the be overused (e.g. chaining can be bad: Until("X") + Until("Y")!).
  """
  
  def __init__(self, lens, **kargs):
    super(Until, self).__init__(**kargs)
    self.lens = self._preprocess_lens(lens)

  def _get(self, concrete_input_reader) :
    
    parsed_chars = ""

    # Parse as many chars as we can until the lens matches something.
    while not concrete_input_reader.is_fully_consumed() :
      try :
        start_state = concrete_input_reader.get_position_state()
        self.lens.get(concrete_input_reader)
        # Roll back the state after successfully getting the lens.
        concrete_input_reader.set_position_state(start_state)
        break
      except LensException:
        pass
      parsed_chars += concrete_input_reader.get_next_char()

    if not parsed_chars :
      raise LensException("Expected to get at least one character!")
    
    return parsed_chars


  def _put(self, abstract_token, concrete_input_reader) :
    # If this is PUT (vs CREATE) then consume input.
    # TODO: Could do with some better checking here, to make sure output cannot be parsed by the lens.
    # Perhaps to verify that we cannot parse the lense within this string.
    lens_assert(isinstance(abstract_token, str)) # Simple check
    if concrete_input_reader :
      self.get(concrete_input_reader)
    
    return abstract_token


  @staticmethod
  def TESTSX() :
    d("Testing")
    concrete_reader = ConcreteInputReader("(in the middle)")
    lens = "("+Until(")", store=True) + ")"
    token = lens.get(concrete_reader, "(in the middle)")
    d(token)
    assert concrete_reader.is_fully_consumed()
    assert token[0] == "in the middle"
    
    # PUT and CREATE
    concrete_reader.reset()
    for cr in [None, concrete_reader] :
      atr = AbstractTokenReader(["monkey"])
      output = lens.put(atr, cr)
      d(output)
      assert output == "(monkey)"


# XXX: Depricated
class Recurse(CombinatorLens):
  """
  During construction, lenses pass up references to Recurse so that it may bind to
  the top level lens, though this must be frozen to the local lens definition.

  TODO: Freeze ascension - will use reflection to freeze when find var to which this Recurse binds.
  TODO: Reconcile different recurse lenses as the same lens (e.g. X + Recurse() + Z | Y + Recurse() + P)
        Only required if we allow multiple instances in lens definition
  """
  def __init__(self, **kargs):
    super(Recurse, self).__init__(**kargs)
    self._bound_lens = None
    return   
    # Let's find which lens we were initialised under.

    

    frame = inspect.currentframe()
    frame = frame.f_back
    d(frame.f_locals)
    return
    #d(frame.f_locals["self"])
    while frame: #"self" in frame.f_locals :
      if "self" in frame.f_locals :
        d(frame.f_locals)
      frame = frame.f_back
    """for i in range(0, callerLevel) :
        callerFrame = callerFrame.f_back
      location = getCallerLocation(callerFrame)
      message = indent + location+": " + message
  """
  
  def bind_lens(self, lens) :
    d("Binding to lens %s" % lens)
    self._bound_lens = lens
  
  def _get(self, concrete_input_reader) :
    assert self._bound_lens, "Recurse was unable to bind to a lens."
    return self._bound_lens._get(concrete_input_reader)

  def _put(self, abstract_data, concrete_input_reader) :
    assert self._bound_lens, "Recurse was unable to bind to a lens."
    return self._bound_lens._put(abstract_data, concrete_input_reader)
 
  # TODO: When Recurse binds, it could replace the links with touching lenses.
  # Or perhaps we override get_next_lenses - perhaps not a problem when it comes to getting char sets
  # since we will be bound by then.
  def get_first_lenses(self):
    return [self]
  def get_last_lenses(self):
    return [self]

  @staticmethod
  def TESTSX() :
    lens = ("[" + (Recurse() | Word(alphas, store=True)) + "]")
    token = lens.get("[[hello]]")
    d(token)
    assert_match(str(token), "...['hello']...")
    output = lens.put(["monkey"], "[[hello]]")
    d(output)
    assert output == "[[monkey]]"


class Forward(CombinatorLens):
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
    self._bound_lens = None
  
  def bind_lens(self, lens) :
    d("Binding to lens %s" % lens)
    assert not self._bound_lens, "The lens cannot be re-bound."
    self._bound_lens = self.coerce_to_lens(lens)
  
  def _get(self, concrete_input_reader) :
    assert self._bound_lens, "Unable to bind to a lens."
    return self._bound_lens._get(concrete_input_reader)

  def _put(self, abstract_data, concrete_input_reader) :
    assert self._bound_lens, "Unable to bind to a lens."
    
    original_limit = sys.getrecursionlimit()
    if self.recursion_limit :
      sys.setrecursionlimit(self.recursion_limit)
    
    try :
      output = self._bound_lens._put(abstract_data, concrete_input_reader)
    except RuntimeError:
      raise InfiniteRecursionException("You will need to alter your grammar, perhaps changing the order of Or lens operands")
    finally :
      sys.setrecursionlimit(original_limit)
    
    return output

 
  # TODO: When Recurse binds, it could replace the links with touching lenses.
  # Or perhaps we override get_next_lenses - perhaps not a problem when it comes to getting char sets
  # since we will be bound by then.
  def get_first_lenses(self):
    return [self]
  def get_last_lenses(self):
    return [self]

  # Use the lshift operator, as does pyparsing, since we cannot easily override (re-)assignment.
  def __lshift__(self, other) :
    assert isinstance(other, BaseLens)
    self.bind_lens(other)


  @staticmethod
  def TESTSX() :
    d("GET")
    lens = Forward()
    # Now define the lens (must use '<<' rather than '=', since cannot easily
    # override '=').
    lens << ("[" + (lens | Word(alphas, store=True)) + "]")
    token = lens.get("[[hello]]")
    d(token)
    assert_match(str(token), "...['hello']...")
    
    
    d("PUT")
    output = lens.put(["monkey"], "[[hello]]")
    d(output)
    assert output == "[[monkey]]"

    # Note that this lens results in infinite recursion upon CREATE.
    d("CREATE")
    try :
      output = lens.create(["world"])
      assert False # should not get here.
    except InfiniteRecursionException:
      pass
    d(output)
    
    # If we alter the grammar slightly, we can overcome this.
    lens = Forward()
    lens << ("[" + (Word(alphas, store=True) | lens) + "]")
    output = lens.create(["world"])
    assert output == "[world]"



