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
import inspect
from nbdebug import d, breakpoint, set_indent_function, IN_DEBUG_MODE
from excepts import *
from util import *
from token_collections import *
from readers import *


# Perhaps can simply be a class.
class Meta:
  LENS = "LENS"
  CONCRETE_INPUT_READER = "CONCRETE_READER"


#########################################################
# Base Lens
#

class Lens(object) :
  
  def __init__(self, type=None, name=None, default=None, **kargs) :
    # Set python type of lense data and a name, for debugging.
    self.type = type
    self.name = name
    if has_value(type) and has_value(default) :
      raise Exception("Cannot set a default value on a lens with a type.")
    self.default = default

    # Composite lenses will store their sub-lenses in here.
    self.lenses = []

    # Allow arbitrary arguments to be set which can aid flexible storage and
    # retrival of items from a container.
    self.kargs = kargs

  def has_type(self) :
    """Determines if this lens will GET and PUT a variable - a STORE lens."""
    return self.type != None


  def get(self, concrete_input, current_container=None) :
      """
      """
      
      # Ensure we have a ConcreteInputReader
      concrete_input_reader = self._normalise_concrete_input(concrete_input)
      assert(has_value(concrete_input_reader))
      
      # The abstract item we will extract from the concret input.
      item = None

      # Get the appropriate container class for our lens, if there is one.
      container_class = self._get_container_class()

      # If we are a container type (e.g. a list or some other AbstractContainer)...
      if container_class :
        # Replace the current container of sub-lenses with our own.
        new_container = container_class()

        # Call get proper, though a container lens' GET proper should not return
        # an item, since its sub-lenses may add items to the current_container.
        assert(self._get(concrete_input_reader, new_container) == None)

        # Since we created the container, we will return it as our item,
        # checking it has the corrent type.
        item = new_container.unwrap()
        assert(type(item) == self.type)

      else :
        # Call GET proper with the current container.
        item = self._get(concrete_input_reader, current_container)

        # Any lens may return an item, though a lens with a type MUST return an
        # item of its specified type.
        if self.has_type() :
          assert(has_value(item))
          # Cast the type (e.g. to an int, float).
          item = self.type(item)
        
      return item
      

  def put(self, item=None, concrete_input=None, current_container=None) :
    
    # Algorithm
    #
    # We will be passed either an item to PUT or a container from which to PUT
    # an item directly or by some descendant lens.
    #
    # If we are a typed lens (i.e. a STORE lens) we will expect to put an item
    # into our PUT proper function (_put) and discared the current container
    # from that branch.
    #   To simplify specific lens definition, we can pluck an item from the
    #   container and pass it to _put
    #   Though if we are a container lens (e.g. list, dict, etc.), we can wrap
    #   the item as a AbstractContainer and replace the current_container.
    #
    # If we are not a typed lens, we have nothing special to do, so simply pass
    # on the arguments to our PUT proper function

    # If there is no concrete input (i.e. for CREATE) and we have a default value, return it.
    if concrete_input == None and has_value(self.default) :
      return str(self.default)

    # Ensure we have a ConcreteInputReader, otherwise None (for CREATE mode).
    concrete_input_reader = self._normalise_concrete_input(concrete_input)

    output = None
    
    # If we are a typed lens, we will expect to PUT an item.
    if self.has_type() :
      # To simplify _put definition, if we were not passed an item, try to pluck
      # one from the current container.
      if not has_value(item) :
        storage_meta_data = self._get_storage_meta_data(concrete_input_reader)
        item = current_container.consume_item(storage_meta_data)

      # We should now have an item suitable for PUTing with our lens.
      assert(has_value(item))
      assert(type(item) == self.type)

      # Now, the item could be a container (e.g. a list, dict, or some other
      # AbstractContainer), so to save the _put definition from having to wrap
      # it for stateful consumption of items, let's do it here.
      item_as_container = ContainerFactory.wrap_container(item)
      if item_as_container :
        # The item is now represted as a consumable container.
        item = None
        current_container = item_as_container
      else :
        # When PUTing a non-container item, should cast to string (e.g. if int
        # passed) and discard current container.
        item = str(item)
        current_container = None

    # Now call PUT proper on our lens.
    output = self._put(item, concrete_input_reader, current_container)
      

    # Return the output, checking it is a string.
    assert(type(output) == str)
    return output
    

  def create(self, item=None, current_container=None) :
    return self.put(item, None, current_container)

  def _normalise_concrete_input(self, concrete_input) :
    # If input a string, wrap in a stateful string reader.
    if concrete_input == None:
      return None
    if isinstance(concrete_input, str) :
      return ConcreteInputReader(concrete_input)
    else :
      return concrete_input

  def _get_container_class(self) :
    # Try to get a container class appropriate for this lens' type, which may be None
    return ContainerFactory.get_container_class(self.type)

  def _get_storage_meta_data(self, concrete_input_reader) :
     # Create some basic meta data to help with storing and retrieving the item.
    meta_data = {
      Meta.LENS: self, # Container can use attributes of lens.
      Meta.CONCRETE_INPUT_READER: concrete_input_reader, # For flexible matching.
    }
    return meta_data


  def _get_and_store_item(self, lens, concrete_input_reader, container) :
    """
    Common function for storing an item in a container with useful meta data
    about its origin, which will allow flexibility in how it is storedd and
    retrieved.
    """

    storage_meta_data = lens._get_storage_meta_data(concrete_input_reader)
    item = lens.get(concrete_input_reader, current_container=container)
    if has_value(item) :
      container.store_item(item, storage_meta_data)


  # XXX: I don't really like these forward declarations, but for now this does
  # the job.  Perhaps lenses can be registered with the framework for more
  # flexible coercion.
  @staticmethod
  def _coerce_to_lens(lens_operand):
    """
    Intelligently converts a type to a lens (e.g. string instance to a Literal
    lens) to ease lens definition; or a class or instance.
    """
    # Coerce string to Literal
    if isinstance(lens_operand, str) :
      lens_operand = Literal(lens_operand)
    # Coerce class to its internally defined lens, such that the lens will GET
    # and PUT instances of that class.
    elif inspect.isclass(lens_operand) and hasattr(lens_operand, "__lens__") :   
      lens_operand = Group(lens_operand.__lens__, type=lens_operand)
    
    assert isinstance(lens_operand, Lens), "Unable to coerce %s to a lens" % lens_operand
    return lens_operand

  def _preprocess_lens(self, lens) :
    """
    Preprocesses a lens to ensure any type-to-lens conversion and for the
    binding of recursive lenses.  This will be called before processing lens arguments.
    """
    lens = Lens._coerce_to_lens(lens)
    return lens



  #-------------------------
  # operator overloads
  #
  
  def __add__(self, other_lens): return And(self, self._preprocess_lens(other_lens))
  def __or__(self, other_lens): return Or(self, self._preprocess_lens(other_lens))

  # Reflected operators, so we can write: lens = "a string" + <some_lens>
  def __radd__(self, other_lens): return And(self._preprocess_lens(other_lens), self)
  def __ror__(self, other_lens): return Or(self._preprocess_lens(other_lens), self)



  #-------------------------
  # For debugging
  #
  
  def _display_id(self) :
    """Useful for identifying specific lenses when debugging."""
    if self.name :
      return self.name
    # If no name, a hash gives us a reasonably easy way to distinguish lenses in debug traces.
    return str(hash(self) % 256)

  # String representation.
  def __str__(self) :
    # Bolt on the class name, to ease debugging.
    return "%s(%s)" % (self.__class__.__name__, self._display_id())
  __repr__ = __str__

  def __instance_name__(self) :
    """Used by nbdebug module to display a custom debug message context string."""
    return self.name or self.__class__.__name__


# XXX: Filler until we rmeove refs to it
class CombinatorLens: pass


##################################################
# Core lenses
#
    
class And(Lens) :
  """A lens that is formed from the ANDing of two sub-lenses."""

  def __init__(self, left_lens, right_lens, **kargs):
   
    super(And, self).__init__(**kargs)

    # Flatten sub-lenses that are also Ands, so we don't have too much nesting,
    # which makes debugging lenses a nightmare.
    for lens in [left_lens, right_lens] :
      if isinstance(lens, self.__class__) : 
        self.lenses.extend(lens.lenses)
      else :
        self.lenses.append(lens)


  def _get(self, concrete_input_reader, current_container) :
    """
    Sequential GET on each lens.
    """
    for lens in self.lenses :
      self._get_and_store_item(lens, concrete_input_reader, current_container)

    # Should not return anything, since we work on the container!


  def _put(self, item, concrete_input_reader, current_container) :
    
    # Simply concatenate output from the sub-lenses.
    output = ""
    for lens in self.lenses :
      output += lens.put(item, concrete_input_reader, current_container)

    return output
    

  @staticmethod
  def TESTS() :
    # These tests flex the use of labels.

    d("GET")
    lens = And( AnyOf(alphas, type=str), AnyOf(alphas, type=str), type=list, somearg="someval")
    got = lens.get("monkey")
    d(got)
    assert(got == ["m", "o"])
    
    d("PUT")
    assert(lens.put(["d", "o"], "monkey") == "do")
 
 
    d("CREATE")
    assert(lens.create(["d", "o"]) == "do")
 
    return


    d("GET")
    lens = AnyOf(alphas, store=True) + AnyOf(nums, store=True, label="2nd_char") + AnyOf(alphas, store=True, is_label=True) + AnyOf(nums, store=True)
    token = lens.get("m1x3p6", check_fully_consumed=False)
    assert_match(str(token), "...<x> ->...")
    assert_match(str(token), "...'2nd_char': ['1']...")
    assert_match(str(token), "...None: ['m', '3']...")

    d("PUT")
    tokens = GenericCollection(["n", "8"])
    tokens["2nd_char"] = "4"
    output = lens.put(tokens, "p2w3z5", check_fully_consumed=False, label="g")
    d(output)
    assert output == "n4g8"

    # CREATE
    d("CREATE")
    d(str(tokens))
    output = lens.create(tokens, label="g")
    assert output == "n4g8"
    
    d("TEST TYPE CASTING")
    lens = And(AnyOf(alphas, store=True) + AnyOf(nums, store=True, type=int), AnyOf(alphas, store=True), type=list)
    assert lens.get("m1x") == ["m", 1, "x"]
    assert lens.put(["n", 4, "d"], "m1x") == "n4d"
    

class Or(CombinatorLens) :
  """
  This is the OR of two lenses.

  To break ties in the GET direction, the longest match is returned; in the PUT
  direction, to ensure tokens do actually get consumed when possible, the
  left-most token-consuming token is favoured, else left-most lens.
  """
  
  def __init__(self, left_lens, right_lens, **kargs):
    super(Or, self).__init__(**kargs)
    self.lenses = []
    left_lens = self._preprocess_lens(left_lens)
    right_lens = self._preprocess_lens(right_lens)

    # Flatten sub-lenses that are also Ors, so we don't have too much nesting, which makes debugging lenses a nightmare.
    for lens in [left_lens, right_lens] :
      if isinstance(lens, self.__class__) :
        self.lenses.extend(lens.lenses)
      else :
        self.lenses.append(lens)


  def _get(self, concrete_input_reader) :
  
    # Algorithm Outline
    #  - More than one lens may match
    #    - Consider AnyOf(alpha) | Empty() -> Empty() will always match
    #    - So test all, and return longest match (i.e. progresses the concrete input the furthest) if several match
    #    - If matches are same length, return firstmost match.
    #  - Note that we must be careful to differentiate between failing to get a token and getting a None token (e.g from Empty())
    # XXX: Perhaps could toggle greedy/non-greedy (i.e. order priority) GET per Or() instance.

    # Remember the starting state (position) of the concrete reader.
    concrete_start_state = concrete_input_reader.get_position_state()
    
    # Try all lenses and store token and end_state
    best_match = None
    for lens in self.lenses :
      try :
        token = lens.get(concrete_input_reader)
        end_state = concrete_input_reader.get_position_state()
        # Check if this is the best match so far, favouring firstmost lenses if equal lengthed parse.
        if not best_match or end_state > best_match[1] :
          best_match = [token, end_state]
      except LensException:
        pass
      
      # Ensure the reader is at the start state for each lens to parse afresh.
      concrete_input_reader.set_position_state(concrete_start_state)

    lens_assert(best_match != None, "Or should match at least one of the lenses")

    # Restore the end state of the best match and return the token.
    concrete_input_reader.set_position_state(best_match[1])
    return best_match[0]

  def _put(self, abstract_data, concrete_input_reader) :
 
    # Algorithm Outline
    #   We may be passed a Token or an AbstractTokenReader
    #   PUT and CREATE:
    #   - Try to (straight) PUT all the lenses and use the firstmost success, favouring lenses that consume abstract tokens.
    #   - Do this first, since we prefer to weave abstract data back into their concrete structure.
    #   PUT
    #   - BUT, if all PUTs fail, try cross-PUTting: GET left lense then CREATE RL, then GET RL CREATE LL - could put this with the CREATE -
    #     since we may have change the abstract from one token type to the other.
    # TODO: Should put longest, perhaps first-most more intuitive for lens designers, so they have some control.
    # TODO: Need to think about recursive lenses, defined with Forward.
    #        Cold process Forward lenses last, but what if we have two forward
    #        lenses?
    
    # Set variable appropriately if we have a token reader (as opposed to a single token).
    if isinstance(abstract_data, AbstractTokenReader) :
      abstract_token_reader = abstract_data
    else :
      abstract_token_reader = None

    # Remember the starting state of the readers - note, conveniently this does nothing if readers are None.
    start_readers_state = get_readers_state(abstract_token_reader, concrete_input_reader)

    d("Trying STRAIGHT PUT.")
    # Try all lenses and store reader and end_state of the longest PUT
    # This handles straight PUTs (vs. cross PUTs) and CREATE (when concrete_input_reader == None)
    best_PUT = None
    lens_consumed_tokens = False # Records if a certain lens consumed a token.
    for lens in self.lenses :

      try :
        # Try PUT on the lens and upon success record the end state.
        output = lens.put(abstract_data, concrete_input_reader)
        end_state = get_readers_state(abstract_token_reader, concrete_input_reader)
        
        # If we are dealing with an AbstractTokenReader, then check to see if
        # the lens consumed any tokens.  otherwise, we assume that it did,
        # since otherwise the PUT (of a specific token) would fail before we
        # got here.
        if abstract_token_reader :
          lens_consumed_tokens = start_readers_state[0] != end_state[0]
        else :
          lens_consumed_tokens = True

        # Update the best action: we prefer the first-most lens that consumes tokens.
        if not best_PUT or (lens_consumed_tokens and not best_PUT[2]) : 
          best_PUT = [output, end_state, lens_consumed_tokens]
          d("BEST straight put: %s" % best_PUT)
          # TODO: Hmmm, but we didn't try the other lens?
          if lens_consumed_tokens : break # We have what we want.
      except LensException:
        pass
      
      # For each lens, ensure the readers state is reset back to the start state.
      set_readers_state(start_readers_state, abstract_token_reader, concrete_input_reader)
      
    # If already we have a PUT that consumed a token, go with those results.
    if best_PUT and best_PUT[2]:
      # Commit to the best end-state.
      set_readers_state(best_PUT[1], abstract_token_reader, concrete_input_reader)
      return best_PUT[0]

    # Handle cross PUTs, which GET (consume) from one lens and CREATE with another.
    if concrete_input_reader :
      d("Trying CROSS PUT.")
      for GET_lens in self.lenses:
        for CREATE_lens in self.lenses :
          if CREATE_lens == GET_lens :
            continue # Already tried straight PUTs
          
          try :
            # Consume with the GET lens, discarding any tokens.
            GET_lens.get(concrete_input_reader)
            # CREATE with the CREATE lens.
            output = CREATE_lens.create(abstract_data)
            # Record the end state, if successful.
            end_state = get_readers_state(abstract_token_reader, concrete_input_reader)
            
            # Again, when we have a reader, check if tokens were consumed, so that we might prioritise.
            if abstract_token_reader :
              lens_consumed_tokens = start_readers_state[0] != end_state[0]
            else :
              lens_consumed_tokens = True
            
            # Update the best action: we prefer the first-most lens that consumes tokens.
            if not best_PUT or (lens_consumed_tokens and not best_PUT[2]) : 
              best_PUT = [output, end_state, lens_consumed_tokens]
            
          except LensException:
            pass
          
          # For new attempt, ensure the readers' state is reset back to the start state.
          set_readers_state(start_readers_state, abstract_token_reader, concrete_input_reader)
          
          if lens_consumed_tokens : break # We have what we want.
        if lens_consumed_tokens : break # Break works only on immediate loop - one of the few justifications for a goto!

    # Now go with our best output.
    if best_PUT :
      set_readers_state(best_PUT[1], abstract_token_reader, concrete_input_reader)
      return best_PUT[0]

    lens_assert(False, "Or should PUT (or CREATE-GET) at least one of the lenses")
     

  def _display_id(self) :
    """For debugging clarity."""
    return " | ".join([str(lens) for lens in self.lenses])

  def get_first_lenses(self):
    """Return list of possible first lenses."""
    first_lenses = []
    for lens in self.lenses :
      first_lenses.extend(lens.get_first_lenses())
    return first_lenses

  def get_last_lenses(self):
    """Return list of possible last lenses."""
    last_lenses = []
    for lens in self.lenses :
      last_lenses.extend(lens.get_last_lenses())
    return last_lenses


  @staticmethod
  def TESTS() :
    d("GET")
    store = True
    lens = AnyOf(nums, store=store, default="4") | AnyOf(alphas, store=store, default="B") | (AnyOf(alphanums, label="l", store=store, default="3") + AnyOf(alphas, store=store, default="x"))
    token = lens.get("2m_x3p6", check_fully_consumed=False)
    d(token)
    assert_match(str(token), "...'l': ['2']...")
    assert_match(str(token), "...None: ['m']...")
    
    d("PUT")
    token["l"] = '8'
    token[0] = 'p'
    output = lens.put(token, "2m_x3p6", check_fully_consumed=False)
    d(output)
    assert output == "8p"
    
    d("CREATE")
    token["l"] = '8'
    token[0] = 'p'
    output = lens.create(token, check_fully_consumed=False)
    d(output)
    assert output == "8p"
   

    # Now see what happens with a non-store lens.
    d("NON-STORE")
    store = False
    lens = AnyOf(nums, store=store) | AnyOf(alphas, store=store, default="B") | (AnyOf(alphanums, label="l", store=store, default="3") + AnyOf(alphas, store=store, default="x"))

    d("GET")
    token = lens.get("2m_x3p6", check_fully_consumed=False)
    d(str(token))
    # This should give us an empty GenericCollection
    assert isinstance(token, GenericCollection) and not token.dict

    d("PUT")
    output = lens.put(token, "2m_x3p6")
    assert output == "2m"
    d(output)
    
    d("CREATE")
    output = lens.create(token)  # Note that token is an empty GenericCollection
    d(output)
    # We expect '3x' (defaults with And's AnyOfs, since the AnyOf lenses reject being passed a token.
    assert output == "3x"
    
    output = lens.create(AbstractTokenReader(token))
    d(output)
    # We expect 'B', since reader does not force tokens on lens and the first AnyOf has no default, the next does,
    # which is 'B'
    assert output == "B"
    

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
  def TESTS() :
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


class Empty(Lens) :
  """
  Matches the empty string, used by Optional().  Can also set modes for special
  empty matches.
  """
  
  # Useful modifiers for empty matches.
  START_OF_TEXT = "START_OF_TEXT"
  END_OF_TEXT   = "END_OF_TEXT"

  def __init__(self, mode=None, **kargs):
    super(Empty, self).__init__(**kargs)
    self.default = ""
    self.mode = mode

  def _get(self, concrete_input_reader) :
    
    if self.mode == self.START_OF_TEXT :
      lens_assert(concrete_input_reader.get_pos() == 0, "Will match only at start of text.")
    elif self.mode == self.END_OF_TEXT :
      lens_assert(concrete_input_reader.is_fully_consumed(), "Will match only at end of text.")

    # Note this is actually a token (not None) we return, that could
    # potentially be stored, so elsewhere in the framework, we need to ensure
    # we check explicitly for None, since "" evaluates to False
    return ""

  def _put(self, abstract_token, concrete_input_reader) :
    # Here we can put only the empty string token.
    lens_assert(isinstance(abstract_token, str) and abstract_token == "")
    return ""

  @staticmethod
  def TESTS() :
    
    # With store
    lens = Empty(store=True)
    assert lens.get("anything", check_fully_consumed=False) == ""
    assert lens.put("", "anything") == ""
    try :
      lens.put(" ", "anything"); assert False
    except LensException :
      pass # The token ' ' is invalid for this lens.
    assert lens.create("") == ""

    # Without store
    lens = Empty()
    assert lens.get("anything", check_fully_consumed=False) == None
    assert lens.put(AbstractTokenReader(GenericCollection()), "anything") == ""
    try :
      lens.put("", "anything"); assert False
    except LensException :
      pass # Even though token valid, this is not a store lens, so will fail.
    
    # Try special modes.
    lens = Empty(mode=Empty.START_OF_TEXT)
    concrete_reader = ConcreteInputReader("hello")
    concrete_reader.get_next_char()
    try : token = lens.get(concrete_reader); assert False, "This should fail - we should not get here!"
    except LensException: pass


class AnyOf(Lens) :
  """
  Matches a single char within a specified set, and can also be negated.
  """
  
  def __init__(self, valid_chars, negate=False, **kargs):
    super(AnyOf, self).__init__(**kargs)
    self.valid_chars, self.negate = valid_chars, negate
 
  def _get(self, concrete_input_reader, current_container) :
    
    char = None
    try:
      char = concrete_input_reader.get_next_char()
      if not self._is_valid_char(char) :
        raise LensException("Expected char %s but got '%s'" % (self._display_id(), truncate(char)))
    except EndOfStringException:
      raise LensException("Expected char %s but at end of string" % (self._display_id()))
    
    return char


  def _put(self, item, concrete_input_reader, current_container) :
    # If this is PUT (vs CREATE) then first consume input.
    if concrete_input_reader :
      self.get(concrete_input_reader)
    lens_assert(isinstance(item, str) and len(item) == 1 and self._is_valid_char(item), "Invalid item '%s', expected %s." % (item, self._display_id()))
    return item


  def _is_valid_char(self, char) :
    """Tests if that passed is a valid character for this lens."""
    if self.negate :
      return char not in self.valid_chars
    else :
      return char in self.valid_chars

  def _display_id(self) :
    """To aid debugging."""
    if self.name :
      return self.name
    if self.negate :
      return "not in [%s]" % range_truncate(self.valid_chars)
    else :
      return "in [%s]" % range_truncate(self.valid_chars)
  

  @staticmethod
  def TESTS() :
    d("GET")
    lens = AnyOf(alphas, type=str)
    token = lens.get("monkey")
    assert token == "m"

    d("PUT")
    output = lens.put("d", "monkey")
    d(output)
    assert output == "d"
    
    d("CREATE")
    lens = AnyOf(alphas, default="x")
    output = lens.create("x")
    d(output)
    assert output == "x"

    d("TEST type coercion")
    lens = AnyOf(nums, type=int)
    assert lens.get("3") == 3
    assert lens.put(8, "3") == "8"


class Group(Lens) :
  """
  A convenience lens that thinly wraps any lens to set a type.
  """

  def __init__(self, lens, **kargs):
    super(Group, self).__init__(**kargs)
    self.lens = self.coerce_to_lens(lens)

  def _get(self, concrete_input_reader) :
    return self.lens.get(concrete_input_reader)

  def _put(self, abstract_token, concrete_input_reader) :
    return self.lens.put(abstract_token, concrete_input_reader)

  @staticmethod
  def TESTS() :
    
    return
    d("GET")
    CONCRETE_STRING = "x=3;z=7;"
    assignment = AnyOf(alphas, is_label=True, store=True) + AnyOf("=", default="=") + AnyOf(nums, store=True) + AnyOf(";", default=";")
    lens = OneOrMore(Group(assignment, store=True))
    token = lens.get(CONCRETE_STRING, check_fully_consumed=False)
    assert token["x"][0] == "3" and token["z"][0] == "7"

    d("PUT")
    token["x"] = ["2"]
    output = lens.put(token, CONCRETE_STRING)
    d(output)
    assert output == "x=2;z=7;"

    d("CREATE")
    output = lens.create(token)
    assert output == "x=2;z=7;"
  
    d("TYPE CASTING TEST")
    values = List(AnyOf(nums, store=True, type=int), ",")
    assign = Group(AnyOf(alphas, is_label=True) + "=" + values + ";", type=list)
    lens = OneOrMore(assign, type=dict)
    token = lens.get("x=1,2,3,4,5;y=2,4,6,8;")
    d(token)
    assert token == {"x":[1,2,3,4,5], "y":[2,4,6,8]}

    output = lens.create({"o":[1,3,5], "e":[2,4,6]})
    d(output)
    # Will be one way around or the other, but some probably find a more deterministic way.
    assert output == "o=1,3,5;e=2,4,6;" or output == "e=2,4,6;o=1,3,5;"


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
  def TESTS() :
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
  def TESTS() :
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
    import inspect

    

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
  def TESTS() :
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
  def TESTS() :
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



##################################################
# Useful lenses
#

class List(And) :
  """Shortcut for defining a lens-delimetered list."""
  def __init__(self, lens, delimiter_lens, **kargs):
    super(List, self).__init__(lens, ZeroOrMore(delimiter_lens + lens), **kargs)

  @staticmethod
  def TESTS() :
    lens = List(Word(alphas, store=True), ",")
    CONCRETE_STRING = "hello,world,again"
    token = lens.get(CONCRETE_STRING)
    d(token)
    assert_match(str(token), "...['hello', 'world', 'again']...")
    output = lens.put(["one", "two"], CONCRETE_STRING)
    d(output)
    assert output == "one,two"

class NewLine(Or) :
  """Matches a newline char or the end of text, so extends the Or lens."""
  def __init__(self, **kargs) :
    super(NewLine, self).__init__(Literal("\n", **kargs), Empty(mode=Empty.END_OF_TEXT))

  @staticmethod
  def TESTS() :
    lens = NewLine()
    assert lens.put(AbstractTokenReader([]), "\n") == "\n"
    output = lens.create(AbstractTokenReader([]))
    assert output == "\n"
    
    lens = NewLine(store=True)
    token = lens.get("\n")
    assert token == "\n"
    
    output = lens.put(AbstractTokenReader(["\n"]), "\n")
    d("'%s'" % output)
    assert output == "\n"
    
    output = lens.create(AbstractTokenReader(["\n"]))
    assert output == "\n"

class Optional(Or) :
  """Wraps an Or with Empty."""
  def __init__(self, lens, **kargs) :
    super(Optional, self).__init__(Empty(), lens, **kargs)
 
  @staticmethod
  def TESTS() :
    for store in [True] :
      # GET
      lens = Optional(Literal("hello123", store=True))
      concrete_reader = ConcreteInputReader("hello123_end")
      token = lens.get(concrete_reader)
      d("token from %s is %s" % (lens, token))

      assert((store and token == "hello123" or token == None) and concrete_reader.get_remaining() == "_end")
      
      # This should be happy not to parse the lens, since Empty() will parse it.
      concrete_reader = ConcreteInputReader("___hello123_end")
      token = lens.get(concrete_reader)
      d(token)
      assert(token == None and concrete_reader.get_remaining() == "___hello123_end")
      
      # PUT - we'd like to show that it will put a token if possible, rather than put Empty, which is always possible.
      concrete_reader = ConcreteInputReader("hello123_end")
      atr = AbstractTokenReader(["hello123"])
      output = lens.put(atr, concrete_reader)
      assert(output == "hello123" and concrete_reader.get_remaining() == "_end")
      if store:
        assert not atr.has_more_tokens_with_label(None)
      else :  
        assert atr.has_more_tokens_with_label(None)
     
      # CREATE
      output = lens.create(AbstractTokenReader(["hello123"]))
      if store:
        assert(output == "hello123")
      else :  
        assert(output == "") # Uses default value of Empty(), the first sub-lens
     
      output = lens.create(AbstractTokenReader([]))
      d(output)
      if store:
        assert(output == "") # Since it looks for but cannot find suitable token, Empty() is created with default value ''.
      else :  
        assert(output == "") # Uses default value of Empty(), the first sub-lens

class ZeroOrMore(Optional) :
  """Simply wraps Optional(OneOrMore(...))"""
  def __init__(self, lens, **kargs):
    super(ZeroOrMore, self).__init__(OneOrMore(lens), **kargs)

  @staticmethod
  def TESTS() :
    # Just test we can build the thing.
    lens = ZeroOrMore(AnyOf(alphas, store=True))
    lens.get("abcd123", check_fully_consumed=False)
    lens.get("123", check_fully_consumed=False)



class Literal(CombineChars) :
  """
  A lens that deals with a constant string, usually that will not be stored.
  """

  def __init__(self, literal_string, **kargs):
    """We create this from CombineChars(AnyOf() + ...) for consistency rather than for efficiency."""

    assert(isinstance(literal_string, str) and len(literal_string) > 0)
    super(Literal, self).__init__(None, **kargs) # Pass None for the lens, which we will build next.
    
    # Build up the lens.
    self.lens = None
    for char in literal_string :
      if not self.lens :
        self.lens = AnyOf(char, store=self.store)
      else :
        self.lens += AnyOf(char, store=self.store)
    
    self.literal_string = literal_string
    self.name = self.name or "'%s'" % truncate(literal_string)

    if not self.default :
      self.default = literal_string

  @staticmethod
  def TESTS() :
    for store in [False, True] :
      # GET
      lens = Literal("hello", store=store)
      concrete_reader = ConcreteInputReader("helloworld")
      token = lens.get(concrete_reader)
      d(token)
      assert((store and token == "hello" or token == None) and concrete_reader.get_remaining() == "world")
      
      # PUT
      concrete_reader.reset()
      output = lens.put(AbstractTokenReader(store and ["hello"] or []), concrete_reader)
      d(output)
      assert(output == "hello" and concrete_reader.get_remaining() == "world")
      
      # CREATE
      output = lens.create(AbstractTokenReader(store and ["hello"] or []))
      d(output)
      assert(output == "hello")

    # Test literal as string concatenation - will fail without correct operator overloading.
    lens = AnyOf("X") + "my_literal"
    lens = "my_literal" + AnyOf("X")  # Uses Lens.__radd__()


class Word(CombineChars) :
  """
  Useful for handling keywords of a specific char range.
  """
  def __init__(self, body_chars, init_chars=None, negate=False, **kargs):
    super(Word, self).__init__(None, **kargs)
     
    if init_chars :
      self.lens = AnyOf(init_chars, negate=negate, store=self.store) + OneOrMore(AnyOf(body_chars, negate=negate, store=self.store))
    else :
      self.lens = OneOrMore(AnyOf(body_chars, negate=negate, store=self.store))

  @staticmethod
  def TESTS() :
    for store in [True, False] :
      # GET
      lens = Word(alphanums, init_chars=alphas, store=store, default="thisis123valid") # A word that can contain but not begin with a number.
      concrete_reader = ConcreteInputReader("hellomonkey123_456")
      token = lens.get(concrete_reader)
      d(token)
      if store :
        assert(token == "hellomonkey123" and concrete_reader.get_remaining() == "_456")
      else :
        assert(concrete_reader.get_remaining() == "_456")
      
      # PUT
      concrete_reader.reset()
      output = lens.put(AbstractTokenReader(["hello456"]), concrete_reader)
      assert(store and output == "hello456" or output == "hellomonkey123" and concrete_reader.get_remaining() == "_456")
      
      # CREATE
      output = lens.create(AbstractTokenReader(["hello456"]))
      assert(store and output == "hello456" or output == "thisis123valid")

    d("Type tests")
    lens = Word(nums, store=True, type=int)
    assert lens.get("3456") == 3456
    assert lens.put(98765, "123") == "98765"


class Whitespace(CombineChars) :
  """
  Whitespace helper lens, that knows how to handle continued lines with '\\n'
  or that preclude an indent.
  """
  
  def __init__(self, default=" ", space_chars=" \t", slash_continuation=False, indent_continuation=False, **kargs):
    # Ensure default gets passed up to parent class - we use default to
    # determine if this lens is optional
    kargs["default"] = default
    super(Whitespace, self).__init__(None, **kargs)
      
    # Set-up a lens the literally matches space.
    spaces = OneOrMore(AnyOf(space_chars, store=self.store))
    self.lens = spaces
    
    # Optionally, augment with a slash continuation lens.
    if slash_continuation :
      self.lens |= Optional(spaces) + "\\\n" + Optional(spaces)
    
    # Optionally, augment with a indent continuation lens.
    if indent_continuation :
      self.lens |= Optional(spaces) + "\n" + spaces 
    
    # If the default string is empty, then make the space optional.
    if default == "" :
      self.lens = Optional(self.lens)
  
  @staticmethod
  def TESTS() :
    lens = Whitespace(" ", store=True) + Word(alphanums, store=True)
    token = lens.get("  \thello")
    assert token[1] == "hello"
    
    lens = Whitespace(" ", store=True, slash_continuation=True) + Word(alphanums, store=True)
    token = lens.get("  \t\\\n  hello")
    assert token[1] == "hello"
    
    lens = Whitespace(" ", store=True, indent_continuation=True) + Word(alphanums, store=True)
    token = lens.get("   \n hello")
    assert token[1] == "hello"


####################################
# Debugging Lenses
#


class NullLens(Lens) :
  """
  When writing new lenses, particularly in a top-down fashion, this lens is
  useful for filling in lens branches that are yet to be completed.
  """
  def _get(self, concrete_input_reader) :
    raise LensException("NullLens always fails, and is useful as a filler for the incremental writing of lenses.")
  def _put(self, abstract_token, concrete_input_reader) :
    raise LensException("NullLens always fails, and is useful as a filler for the incremental writing of lenses.")

####################################
# Utility functions
#


def lens_assert(condition, message=None) :
  """
  Useful for assertion within lenses that should raise LensException, such that
  higher-level parsing may be resume, perhaps on an alternate branch.
  """
  if not condition :
    raise LensException(message)


##################################
# Useful definitions
#

# Some useful character sets.
import string
alphas    = string.lowercase + string.uppercase
nums      = string.digits
hexnums   = nums + "ABCDEFabcdef"
alphanums = alphas + nums

# Some lens abbreviations
ZM  = ZeroOrMore
OM  = OneOrMore
O   = Optional
G   = Group
WS  = Whitespace


##################################
# Useful API functions, particularly since they coerce the first arg to a lens.
#

def get(lens, *args, **kargs) :
  lens = BaseLens.coerce_to_lens(lens)
  return lens.get(*args, **kargs)

def put(lens_or_instance, *args, **kargs) :
  
  # If we have an instance of a class which defines its own lens...
  if hasattr(lens_or_instance, "__lens__") :
    # Might as well still coerce the lens, just in case.
    lens = BaseLens.coerce_to_lens(lens_or_instance.__lens__)
    instance = lens_or_instance # For clarity.
    return lens.put(instance, *args, **kargs)
  
  # Otherwise...
  lens = BaseLens.coerce_to_lens(lens_or_instance)
  return lens.put(*args, **kargs)

create = put

class HighLevelAPITest:
  @staticmethod
  def TESTS() :
    CONCRETE_STRING = "Person:name=albert;surname=camus"
    class Person(object): # Must be new-style class
      __lens__ = "Person" + ":" + List(Group(Word(alphas, is_label=True) + "=" + Word(alphas, store=True), type=auto_list), ";")

      def __init__(self, name, surname) :
        self.name, self.surname = name, surname

      def __str__(self) :
        return "Person: name -> %s, surname -> %s" % (self.name, self.surname)

    d("GET")
    person = get(Person, CONCRETE_STRING)
    assert (type(person) == Person)
    d(person)
    assert(person.name == "albert" and person.surname == "camus")

    d("PUT")
    person.name = "nick"
    person.surname = "blundell"
    output = put(person, CONCRETE_STRING)
    d(output)
    assert(output == "Person:name=nick;surname=blundell")

    d("CREATE")
    fred = Person("fred", "flintstone")
    output = create(fred)
    d(output)
    assert(output == "Person:name=fred;surname=flintstone" or output == "Person:surname=flintstone;name=fred")


###########################
# Debugging stuff.
#

# TODO: Move this out to a debug module.

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


###########################
# Main.
#

def main() :
  # This can be useful for quick testing.
  d("Testing")

if __name__ == "__main__":
  main()
