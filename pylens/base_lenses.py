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
from debug import *
from exceptions import *
from containers import *
from readers import *
from util import *
from charsets import *


#########################################################
# Base Lens
#########################################################

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
    self.options = Properties(kargs)

    # There is no point setting a non-store lens as a label, so set type as str.
    if not has_value(self.type) and self.options.is_label :
      self.type = str

  def has_type(self) :
    """Determines if this lens will GET and PUT a variable - a STORE lens."""
    return self.type != None


  def get(self, concrete_input, current_container=None) :
      """
      """
      #
      # Algorithm
      #
      # If we have a container type
      #   replace container with new one - to save hassle of doing it in each _get 
      # item = _get(input, container)
      # if typed_lens:
      #   cast item if not instance
      #   assert(item is correct type)
      #   if auto_list :
      #     item = unwrap item
      #   assert not already got properties
      #   set properties
      #
      # Note, even if non-typed, we may return an item from a lens we wrap (e.g. Or)
      #
      # return item

      

      # Ensure we have a ConcreteInputReader
      assert(has_value(concrete_input))
      concrete_input_reader = self._normalise_concrete_input(concrete_input)
      
      # Get the appropriate container class for our lens, if there is one.
      container_class = self._get_container_class()

      # Remember the start position of the concrete reader, to aid
      # abstract--concrete matching.
      start_position = concrete_input_reader.get_pos()

      # Replace the current container of sub-lenses with our own.
      if container_class :
        new_container = container_class()
        # Call GET proper with our container, checking that no item is returned,
        # since all items should be stored WITHIN the container
        assert(self._get(concrete_input_reader, new_container) == None)
        
        # Since we created the container, we will return it as our item,
        item = new_container.unwrap()
      else :
        # Call GET proper.
        item = self._get(concrete_input_reader, current_container)

      if self.has_type() :
        # Cast the item to our type.
        if not isinstance(item, self.type) :
          item = self.type(item)

        # Handle auto_list (i.e. unwrap single item from list)
        if self.type == auto_list :
          # XXX: Have to be careful with source meta data here.
          # Check we got a list.
          assert(isinstance(item, list))
          if len(item) == 1 :
            item = item[0]
        else :
          # Check we got an item of the correct type (after any casting).
          assert(isinstance(item, self.type))

        # Now add source info to the item.
        # XXX: May also be useful to add end position.
        item = self._attach_source_meta_data(item, start_position, concrete_input_reader)


      return item


  def put(self, item=None, concrete_input=None, current_container=None) :
    
    # Algorithm
    #
    # We will be passed either an item to PUT or a container from which to PUT
    # an item directly or by some descendant lens.
    #
    # If we are a typed lens (i.e. a STORE lens) we will expect to put an item
    # into our PUT proper function (_put)
    #   To simplify specific lens definition if we are a container lens (e.g.
    #   list, dict, etc.), we can wrap the item as a AbstractContainer and
    #   replace the current_container of this branch.
    #
    # If we are not a typed lens, we have nothing special to do, so simply pass
    # on the arguments to our PUT proper function, noting that we could still
    # have been passed an item from the user.

    # If there is no concrete input (i.e. for CREATE) and we have a default value, return it.
    if concrete_input == None and has_value(self.default) :
      return str(self.default)

    # Ensure we have a ConcreteInputReader, otherwise None (for CREATE mode).
    concrete_input_reader = self._normalise_concrete_input(concrete_input)

    output = None
    
    # If we are a typed lens, we will expect to PUT an item.
    if self.has_type() :
      
      # A typed lens expects some item to put.
      assert(has_value(item))
      
      # If we are of type auto_list, wrap item in list if necessary.
      if self.type == auto_list :
        if not isinstance(item, list) :
          # Ensure wrapped item preserves source_meta_data.
          item_as_list = list_wrapper([item])
          if hasattr(item, "source_meta_data") :
            item_as_list.source_meta_data = item.source_meta_data
            item.source_meta_data = None
          item = item_as_list

      else : 
        # We should now have an item suitable for PUTing with our lens.
        if not isinstance(item, self.type) :
          raise LensException("This lens cannot PUT an item of that type")

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

  def get_and_discard(self, concrete_input, current_container) :
    """
    Sometimes we wish to consume input but discard any items.
    Note, since some lenses might one day use the current container state we must first
    store items in the container before reverting it.  For example, the opening
    and closing tags in XML-like structures.
    """
    # If we have a container, store its start state.
    if has_value(current_container): container_start_state = current_container._get_state()

    # Issue the get.
    self.get(concrete_input, current_container)


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

  def _attach_source_meta_data(self, item, start_position, concrete_input_reader) :
    """Adds meta data to an item, indicating its origin in the concrete input."""
    # There is a problem with the lens definition if an item already has
    # this.
    assert(has_value(item) and not hasattr(item, "source_meta_data"))

    if isinstance(item, (str)) : item = str_wrapper(item)
    if isinstance(item, (float)) : item = float_wrapper(item)
    if isinstance(item, (int)) : item = int_wrapper(item)
    if isinstance(item, (list)) : item = list_wrapper(item)
    if isinstance(item, (dict)) : item = dict_wrapper(item)
    
    item.source_meta_data = Properties()
    item.source_meta_data.start_position = start_position
    item.source_meta_data.concrete_input_reader = concrete_input_reader
    item.source_meta_data.lens = self
    return item

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


#########################################################
# Core lenses
#########################################################
    
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
      current_container.get_and_store_item(lens, concrete_input_reader)

    # Should not return anything, since we work on the container!


  def _put(self, item, concrete_input_reader, current_container) :
    
    # Simply concatenate output from the sub-lenses.
    output = ""
    for lens in self.lenses :
      output += current_container.consume_and_put_item(lens, concrete_input_reader)

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


class Or(Lens) :
  """
  This is the OR of two lenses.

  To break ties in the GET direction, the longest match is returned; in the PUT
  direction, to ensure tokens do actually get consumed when possible, the
  left-most token-consuming token is favoured, else left-most lens.
  """
  
  def __init__(self, left_lens, right_lens, **kargs):
    super(Or, self).__init__(**kargs)
    left_lens = self._preprocess_lens(left_lens)
    right_lens = self._preprocess_lens(right_lens)

    # Flatten sub-lenses that are also Ors, so we don't have too much nesting, which makes debugging lenses a nightmare.
    for lens in [left_lens, right_lens] :
      if isinstance(lens, self.__class__) :
        self.lenses.extend(lens.lenses)
      else :
        self.lenses.append(lens)


  def _get(self, concrete_input_reader, current_container) :
    
    # Try each lens until the firstmost succeeds.
    for lens in self.lenses :
      try :
        with automatic_rollback(concrete_input_reader, current_container) :
          return lens.get(concrete_input_reader, current_container)
      except LensException:
        pass
        
    raise LensException("We should have GOT one of the lenses.")


  def _put(self, item, concrete_input_reader, current_container) :
    
    # First we try a straight PUT (i.e. the lens both consumes from input and puts from the container)
    for lens in self.lenses :
      try :
        with automatic_rollback(concrete_input_reader, current_container) :
          return lens.put(item, concrete_input_reader, current_container)
      except LensException:
        pass

    # Failing a straight PUT we need to do a GET with one lens then CREATE with another.
    # Note that, though we will not use any items from the GET it must be allowed to modify a copy of current_container.
    # This means that the successful GET may consume from the concrete input, though must have its changes to the container
    # discarded.


    # Now, if we fail a straight put, we must GET with one lens (to consume
    # input, not to store any items), then CREATE with another; so we must make
    # sure to revert the container after a successful GET.  It is tempting here
    # to create a dummy container rather than copying it, but we might later
    # define lenses that can alter their behaviour based on the current state of
    # the container.
    GET_succeeded = False
    for lens in self.lenses :
      try :
        with automatic_rollback(concrete_input_reader, current_container) :
          lens.get_and_discard(concrete_input_reader, current_container)
          GET_succeeded = True
          break
      except LensException:
        pass

    if not GET_succeeded:
      raise LensException("Cross-put GET failed.")

    # Now we must CREATE with one of the lenses.
    for lens in self.lenses :
      try :
        with automatic_rollback(current_container) :
          return lens.create(item, current_container)
      except LensException:
        pass

    raise LensException("We should have PUT one of the lenses.")
    

  def _display_id(self) :
    """For debugging clarity."""
    return " | ".join([str(lens) for lens in self.lenses])


  @staticmethod
  def TESTS() :
    
    d("GET")
    lens = AnyOf(alphas, type=str) | AnyOf(nums, type=int)
    concrete_input_reader = ConcreteInputReader("abc")
    got = lens.get(concrete_input_reader)
    assert(got == "a" and concrete_input_reader.get_remaining() == "bc")
    concrete_input_reader = ConcreteInputReader("123")
    got = lens.get(concrete_input_reader)
    assert(got == 1 and concrete_input_reader.get_remaining() == "23")

    d("PUT")
    assert(lens.put(5, "123") == "5")
    assert(lens.put("z", "abc") == "z")
    concrete_input_reader = ConcreteInputReader("abc")
    assert(lens.put(5, concrete_input_reader) == "5" and concrete_input_reader.get_remaining() == "bc")
    assert(lens.put("z", "123") == "z")
    
    d("CREATE")
    assert(lens.create(5) == "5")
    assert(lens.create("a") == "a")


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
   
    if self.has_type() :
      return char
    else :
      return None


  def _put(self, item, concrete_input_reader, current_container) :
    
    # If we are not a store lens, simply return what we would consume from the input.
    if not self.has_type() :
      # We should not have been passed an item.
      assert(not has_value(item))
      if has_value(concrete_input_reader) :
        start_position = concrete_input_reader.get_pos()
        self._get(concrete_input_reader, current_container)
        return concrete_input_reader.get_consumed_string(start_position)
        
      else :
        raise NoDefaultException("Cannot CREATE: a default should have been set on this lens, or a higher lens.")
    
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

    d("Test non-typed lens")
    lens = AnyOf(alphas, default="d")
    assert(lens.put(None,"a") == "a")
    assert(lens.create(None) == "d")
    lens = AnyOf(alphas)
    with assert_raises(NoDefaultException) :
      lens.create(None)
    

class Repeat(Lens) :
  """
  Applies a repetition of the givien lens (i.e. kleene-star).
  """

  def __init__(self, lens, min_count=1, max_count=None, infinity_limit=1000, **kargs):
    super(Repeat, self).__init__(**kargs)
    self.min_count, self.max_count = min_count, max_count
    self.infinity_limit = infinity_limit
    self.lenses = [self._coerce_to_lens(lens)]

  def _get(self, concrete_input_reader, current_container) :
    
    # For brevity.
    lens = self.lenses[0]
    
    # Try to get as many as we can, up to a maximum if set.
    no_succeeded = 0
    while(True) :
      try :
        with automatic_rollback(concrete_input_reader, current_container) :
          # TODO: What if there is no container???
          current_container.get_and_store_item(lens, concrete_input_reader)
          no_succeeded += 1
      except LensException :
        break

      # Don't get more than maximim
      if has_value(self.max_count) and no_succeeded == self.max_count :
        break

      # Check for infinite iteration (i.e. if lens does not progress state)
      if has_value(self.infinity_limit) and no_succeeded >= self.infinity_limit :
        raise InfiniteIterationException("Lens may iterate indefinitely - must be redesigned")

    # Something with the algorthm has gone wrong if this fails.
    if has_value(self.max_count) :
      assert(no_succeeded <= self.max_count)

    if no_succeeded < self.min_count :
      raise LensException("Expected at least %s successful GETs" % (self.min_count))
    


  def _put(self, item, concrete_input_reader, current_container) :

    # For brevity.
    lens = self.lenses[0]

    no_succeeded = 0
    no_put = 0
    output = ""
    
    # This first tries to PUT (if we have concrete input) then tries to CREATE
    # (by effectively setting the concrete reader to None).
    effective_concrete_reader = concrete_input_reader
    while True :
      try :
        with automatic_rollback(effective_concrete_reader, current_container) :
          output += current_container.consume_and_put_item(lens, effective_concrete_reader)
          no_succeeded += 1
      except LensException:
        # If we fail and the effective_concrete_reader is set, we may now
        # attempt some CREATEs by setting the reader to None for the next
        # iteration.
        if has_value(effective_concrete_reader) :
          effective_concrete_reader = None
          continue
        else :
          break

      # Later on, for the GETs, we need to know how many were PUT (vs. CREATED).
      if has_value(effective_concrete_reader) :
        no_put = no_succeeded

      # Don't get more than maximim
      if has_value(self.max_count) and no_succeeded == self.max_count :
        break

      # Check for infinite iteration (i.e. if lens does not progress state)
      if has_value(self.infinity_limit) and no_succeeded >= self.infinity_limit :
        raise InfiniteIterationException("Lens may iterate indefinitely - must be redesigned")
    
    # Something with algorthm has gone wrong if this fails.
    if has_value(self.max_count) :
      assert(no_succeeded <= self.max_count)

    if no_succeeded < self.min_count :
      raise LensException("Expected at least %s successful GETs" % (self.min_count))
  
   
    # Finally, the items we PUT/CREATED may be fewer than the number of concrete
    # structures, so we GET as many as possible, discarding any extracted items
    # by reseting the container state after this process.
    if has_value(concrete_input_reader) :
      
      # Determine how many we need to get to consume max from input.
      if has_value(self.max_count) :
        no_to_get = self.max_count - no_put
        assert(no_to_get >= 0)
      
      no_got = 0
      state = get_rollbackables_state(current_container)
      while True :
        try :
          with automatic_rollback(concrete_input_reader) :
            #lens.get(concrete_input_reader, current_container)
            current_container.get_and_store_item(lens, concrete_input_reader)
            no_got += 1
        except LensException:
          break

        if has_value(self.max_count) and no_got == no_to_get :
          break
      # Discard any items added by the lens.
      set_rollbackables_state(state, current_container)

    return output


  @staticmethod
  def TESTS() :
    
    lens = Repeat(AnyOf(nums, type=int), min_count=3, max_count=5, type=list)
    d("GET")
    assert(lens.get("1234") == [1,2,3,4])
    with assert_raises(LensException) :
      lens.get("12")
    assert(lens.get("12345678") == [1,2,3,4,5])

    d("PUT")
    assert(lens.put([1,2,3,4,5], "98765") == "12345")
    assert(lens.put([1,2,3,4,5,6], "987654321") == "12345")
    assert(lens.put([1,2,3,4,5,6], "981") == "12345")
    input_reader = ConcreteInputReader("87654321")
    assert(lens.put([1,2,3,4], input_reader) == "1234")
    assert(input_reader.get_remaining() == "321")

    assert(lens.create([1,2,3,4]) == "1234")
    with assert_raises(LensException) :
      lens.create([1,2])
    assert(lens.create([1,2,3,4,5,6,7,8]) == "12345")

    # Test infinity problem
    lens = Repeat(Empty(), min_count=3, max_count=None, infinity_limit=5, type=list)
    with assert_raises(InfiniteIterationException) :
      lens.get("anything")
    with assert_raises(InfiniteIterationException) :
      lens.put([], "anything")

    # Test non-typed and default
    # XXX
    lens = Repeat(AnyOf(nums))
    #d(lens.get("12345"))


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

  def _get(self, concrete_input_reader, current_container) :
    if self.mode == self.START_OF_TEXT :
      if concrete_input_reader.get_pos() != 0 :
        raise LensException("Will match only at start of text.")
    elif self.mode == self.END_OF_TEXT :
      if not concrete_input_reader.is_fully_consumed() :
        raise LensException("Will match only at end of text.")

    # Note thaht, useless as it is, this is actually an item that could potentially be stored that we
    # return, which is why we must explicitly check for None elsewhere in the
    # framework, since "" == False but "" != None.
    return ""

  def _put(self, item, concrete_input_reader, current_container) :
    # XXX: Should check for start or end of text here, but what about CREATE?
    
    # Here we can put only the empty string token, though if this lens does not
    # store an item, the default value of "" will intercept this function being called.
    if not (isinstance(item, str) and item == "") :
      raise LensException("Expected to put an empty string")
    return ""

  @staticmethod
  def TESTS() :
    
    # Test with and without type
    for lens in [Empty(type=str), Empty()] :
      lens = Empty()
      assert lens.get("anything") == ""
      assert lens.put("", "anything") == ""
      with assert_raises(LensException) :
        lens.put(" ", "anything")
      assert lens.create("") == ""
    
    # Try special modes.
    lens = Empty(mode=Empty.START_OF_TEXT)
    concrete_reader = ConcreteInputReader("hello")
    concrete_reader.get_next_char()
    with assert_raises(LensException) : 
      lens.get(concrete_reader)
    
    lens = Empty(mode=Empty.END_OF_TEXT)
    concrete_reader = ConcreteInputReader("h")
    with assert_raises(LensException) : 
      lens.get(concrete_reader)
    concrete_reader.get_next_char()
    lens.get(concrete_reader)



class Group(Lens) :
  """
  A convenience lens that thinly wraps any lens to set a type.
  """

  def __init__(self, lens, **kargs):
    super(Group, self).__init__(**kargs)
    self.lenses = [self._coerce_to_lens(lens)]

  def _get(self, concrete_input_reader, current_container) :
    return self.lenses[0].get(concrete_input_reader, current_container)

  def _put(self, item, concrete_input_reader, current_container) :
    return self.lenses[0].put(item, concrete_input_reader, current_container)

  @staticmethod
  def TESTS() :
   
    d("GET")
    lens = Group(AnyOf(alphas,type=str) + AnyOf(nums, type=int), type=list)
    got = lens.get("a2b3")
    d(got)
    assert(got == ["a", 2])

    d("PUT")
    assert(lens.put(["x", 4], "a2b3") == "x4")

    d("CREATE")
    assert(lens.put(["x", 4]) == "x4")
