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
from item import *
from util import *
from charsets import *


#########################################################
# Base Lens
#########################################################

class Lens(object) :
  
  def __init__(self, type=None, name=None, default=None, **kargs) :
    
    # Set python type of lens data and a name, for debugging.
    self.type = type
    self.name = name
    if has_value(type) and has_value(default) :
      raise Exception("Cannot set a default value on a lens with a type (i.e. on a store lens).")
    self.default = default

    # Composite lenses will store their sub-lenses in here.
    self.lenses = []

    # Allow arbitrary arguments to be set which can aid flexible storage and
    # retrival of items from a container.
    self.options = Properties(kargs)

    #
    # Argument shortcuts
    #

    # There is no point setting a non-store lens as a label, so set type as str.
    if not has_value(self.type) and self.options.is_label :
      self.type = str


  def get(self, concrete_input, current_container=None) :
    """
    Handles input normalisation and common functions of a GET call on a lens.
    """
    #
    # Algorithm
    #
    # If we have a container type
    #   replace container with new one - to save hassle of doing it in each
    #   _get (proper), since a typed-container lens will always deal with its
    #   own container
    # item = _get(input, container)
    # if typed_lens:
    #   cast item if not instance
    #   assert(item is correct type)
    #   assert not already got properties
    #   set properties
    #
    # Note, even if non-typed, we may return an item from a lens we wrap (e.g. Or)
    #
    # item = process_item(item) # e.g. allow pre-processing of item (e.g. for auto_list)
    #
    # return item

    # Ensure we have a ConcreteInputReader
    assert_msg(has_value(concrete_input), "Cannot GET if there is no input string!")
    concrete_input_reader = self._normalise_concrete_input(concrete_input)
  
    if IN_DEBUG_MODE :
      d("Initial state: in={concrete_input_reader}, cont={current_container}".format(
        concrete_input_reader = concrete_input_reader,
        current_container = current_container,
      ))

    # Create the appropriate container class for our lens, if there is one.
    new_container = self._create_container()

    # Remember the start position of the concrete reader, to aid
    # abstract--concrete matching.
    start_position = concrete_input_reader.get_pos()

    # If we are a container-creating lens, replace the current container of
    # sub-lenses with our own container (new_container).
    if new_container :
      # Call GET proper with our container, checking that no item is returned,
      # since all items should be stored WITHIN the container
      assert_msg(self._get(concrete_input_reader, new_container) == None, "Container lens %s has GOT an item, but all items must be stored in the current container." % self)
      
      # Since we created the container, we will return it as our item,
      item = new_container.unwrap()
    else :
      # Call GET proper.
      item = self._get(concrete_input_reader, current_container)

    if self.has_type() :
      
      # Cast the item to our type (usually if it is a string).
      if not isinstance(item, self.type) :
        item = self.type(item)

      # Double check we got an item of the correct type (after any casting).
      assert(isinstance(item, self.type))
     
      # Attach meta data to the item (e.g. cast it to a wrapper class if type
      # does not support adding new attributes).
      item = attach_meta_data(item)
      
      # Now add source info to the item.
      item._meta_data.lens = self
      item._meta_data.start_position = start_position
      item._meta_data.concrete_input_reader = concrete_input_reader

    if IN_DEBUG_MODE :
      d("GOT: %s" % (item == None and "NOTHING" or item))
    
    # Pre-process outgoing item.
    item = self._process_outgoing_item(item)

    return item

  # TODO: Add label of item.
  def put(self, item=None, concrete_input=None, current_container=None, label=None) :
   
    #
    # Algorithm
    #
    # Assert item => container = None
    # Note, though an item will hold its own input, the lens must consumed from
    # the outer input reader if one is supplied.
    #
    # Normalise concrete input reader.
    #
    # If we are an un-typed lens
    #   if we have a default value and no concrete input, return it.
    #   otherwise return put proper, passing through our args - note, item could be passed through us
    #
    # Now assumed we are typed lens
    #
    #  If we are passed an item
    #    ensure meta attached
    #    pre-process item (e.g. to handle auto_list)
    #    check correct type, else raise LensException
    #    get the item input reader if there is one - can be None
    #    if item_input_reader 
    #      if input_reader
    #        if item_input_reader is not aligned with (outer) input_reader
    #          consume from input_reader
    #          set input_reader item_input_reader
    #        else we use the input_reader (i.e both consume and put) - can discard item_input_reader
    #    else :
    #      No input for this item, so we are CREATING
    #      if input_reader
    #        consume from input_reader
    #      set input_reader = None
    #      
    #    if we are container type, wrap item as current_container and set item = None
    #    call put proper on item with item, input_reader and current_container
    #  else if we are passed a container (and no item)
    #    instruct the container to put it.
    #
    #  Should have returned by here, so raise LensException: expected something to put.
    #

    # If we are passed an item, we do not expect an outer container to also have
    # been passed.
    if has_value(item) :
      assert_msg(current_container == None, "A lens should not be passed both a container and an item.")

      # XXX: The following does not account for lenses that use a container and poss. input to pluck their item.
      #if self.has_type() :
      #  assert_msg(concrete_input == None, "A typed lens should not be passed the outer concrete input.")

    # Ensure we have a ConcreteInputReader, otherwise None (for CREATE mode).
    concrete_input_reader = self._normalise_concrete_input(concrete_input)

    if IN_DEBUG_MODE :
      d("Initial state: item={item}, in={concrete_input_reader}, cont={current_container}".format(
        item = item,
        concrete_input_reader = concrete_input_reader,
        current_container = current_container,
      ))

    # Handle cases where our lens does not directly store an item.
    if not self.has_type() :
      # Use default for CREATE
      if concrete_input == None and has_value(self.default) :
        return str(self.default)
      # Otherwise do a PUT proper, passing through our arguments, for example
      # our child lens may put an item directly or from the container.
      output = self._put(item, concrete_input_reader, current_container)
      d("PUT: %s" % output or "NOTHING")
      return output


    # Now we can assume our lens has a type (i.e. directly stores/consumes an
    # item)
    if has_value(item) :
    
      # For the sake of consistancy, ensure the incoming item can hold meta data.
      item = attach_meta_data(item)
      
      # Associate a label with the item (usually a label passed from user which is required internally by a structure)
      item._meta_data.label = label

      # Pre-process the incoming item (e.g to handle auto_list)
      item = self._process_incoming_item(item)
     
      if not isinstance(item, self.type) :
        raise LensException("This lens %s of type %s cannot PUT an item of that type %s" % (self, self.type, type(item)))
      
      # If this item was previously GOTten, we can get its original input.
      if item._meta_data.concrete_input_reader :
        item_input_reader = ConcreteInputReader(item._meta_data.concrete_input_reader)
        item_input_reader.set_pos(item._meta_data.start_position)

        # If the readers are not aligned...
        if not(has_value(concrete_input_reader) and item_input_reader.is_aligned_with(concrete_input_reader)) :
          # Consumed from the outer reader, if there is one.
          if has_value(concrete_input_reader) :
            d("Inputs not aligned, so consuming and discarding from outer input reader.")
            self.get_and_discard(concrete_input_reader, current_container)
          # Now use substitute the outer reader (if there was one) with our
          # item's reader
          concrete_input_reader = item_input_reader
      else :
        # Otherwise, if our item had no source meta, we will be CREATING.
        if has_value(concrete_input_reader) :
          d("Inputs not aligned, so consuming and discarding from outer input reader.")
          self.get_and_discard(concrete_input_reader, current_container)
        concrete_input_reader = None
      
      # Now, the item could be a container (e.g. a list, dict, or some other
      # AbstractContainer), so to save the _put definition from having to wrap
      # it for stateful consumption of items, let's do it here.
      item_as_container = ContainerFactory.wrap_container(item, container_lens=self)
      if item_as_container :
        # The item is now represented as a consumable container.
        item = None
        current_container = item_as_container
      else :
        # When PUTing a non-container item, should cast to string (e.g. if int
        # passed) and discard current container.
        item = str(item)
        current_container = None

      # Now call PUT proper on our lens.
      output = self._put(item, concrete_input_reader, current_container)
      d("PUT: %s" % output or "NOTHING")
      return output
   
    # If instead of an item we have a container, instruct the container to put
    # an item into the lens.
    elif has_value(current_container) :
      assert(isinstance(current_container, AbstractContainer))
      output = current_container.consume_and_put_item(self, concrete_input_reader)
      d("PUT: %s" % output or "NOTHING")
      return output

    # We should have returned by now.
    raise LensException("This typed lens expected to PUT an item either directly or from a container.")


  #XXX: Will be depreciated, since now implicit in put.
  def create(self, item=None, current_container=None) :
    raise Exception("Deprecated")
    return self.put(item, None, current_container)

  def get_and_discard(self, concrete_input, current_container) :
    """
    Sometimes we wish to consume input but discard any items GOTten.
    Note, it is tempting to somehow not use the current_container, though some lenses might
    one day use the current container state, so we must first store items in the
    container before reverting it.  For example, the opening and closing tags in
    XML-like structures.
    """
    # If we have a container, store its start state.
    if has_value(current_container): container_start_state = current_container._get_state()

    # Issue the get.
    self.get(concrete_input, current_container)
    
    # Now revert the state.
    if has_value(current_container): current_container._set_state(container_start_state)


  def has_type(self) :
    """Determines if this lens will GET and PUT a variable - a STORE lens."""
    return self.type != None

  def item_is_compatible_type(self, item) :
    """Checks if this item is of type compatible with this lens."""
    pass

  #
  # container_get and container_put are used by container lenses to store and
  # put items from a container, whilst cleaninly handling the case where there
  # is no container (e.g. repetition of non-store lenses, etc.)
  #

  def container_get(self, lens, concrete_input_reader, current_container) :
    """Wraps get_and_store_item if we have a container."""
    if has_value(current_container) :
      current_container.get_and_store_item(lens, concrete_input_reader)
    else :
      # Call get on lens passing no container, checking it returns no item.
      assert_msg(lens.get(concrete_input_reader, None) == None,
        "The untyped container lens %s did not expect the sub-lens %s to return an item" % (self, lens)
      )

  def container_put(self, lens, concrete_input_reader, current_container) :
    """Wraps consume_and_put_item if we have a container."""
    if current_container :
      return current_container.consume_and_put_item(lens, concrete_input_reader)
    else :
      # Otherwise, we PUT with no abstract data (e.g. for non-store sublenses)
      return lens.put(None, concrete_input_reader, None)


  #
  # Helper methods.
  #

  def _normalise_concrete_input(self, concrete_input) :
    # If input a string, wrap in a stateful string reader.
    if concrete_input == None:
      return None
    if isinstance(concrete_input, str) :
      return ConcreteInputReader(concrete_input)
    else :
      return concrete_input

  def _create_container(self):
    """Creates a container for this lens, if lens of appropriate type."""
    return ContainerFactory.create_container(self)


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
    Preprocesses a lens to enable type-to-lens conversion. This will be
    called before processing lens arguments.
    """
    lens = Lens._coerce_to_lens(lens)
    return lens


  #
  # Allow the potential modification of incoming and outgoing items (e.g. to handle auto_list)
  #

  def _process_outgoing_item(self, item) :
    
    if self.options.auto_list == True and self.has_type() and issubclass(self.type, list) and len(item) == 1:
      # This allows a list singleton to be returned as a single item, for
      # convenience.
      # The easy part is extracting a singleton from the list, but we must
      # preserve the source meta data of the list item by piggybacking it onto
      # the extracted item's meta data

      # TODO: Need to ensure piggybacked meta data gets flexed in the tests.
      list_meta_data = item._meta_data
      singleton_meta_data = item[0]._meta_data
      item = item[0]
      item._meta_data = list_meta_data
      item._meta_data.singleton_meta_data = singleton_meta_data
      
    return item


  def _process_incoming_item(self, item) :
   
    if self.options.auto_list == True and self.has_type() and issubclass(self.type, list) and not isinstance(item, list):
      # Expand an item into a list, being careful to restore any meta data.

      # Create some variables to clarify the process.
      singleton = item
      list_meta_data = item._meta_data
      singleton_meta_data = item._meta_data.singleton_meta_data
      
      # Safeguard to ensure piggybacked data cannot be used more than once.
      list_meta_data.singleton_meta_data = None
      
      # Wrap the singleton in a list, giving it the meta_data of the item.
      item = list_wrapper([singleton])
      item._meta_data = list_meta_data

      # Ensure the singleton has its meta data restored, if it was maintained.
      if singleton_meta_data :
        singleton._meta_data = singleton_meta_data

    return item


  #-------------------------
  # operator overloads
  #
  
  def __add__(self, other_lens): return And(self, self._preprocess_lens(other_lens))
  def __or__(self, other_lens): return Or(self, self._preprocess_lens(other_lens))

  # Reflected operators, so we can write: lens = "a string" + <some_lens>
  def __radd__(self, other_lens): return And(self._preprocess_lens(other_lens), self)
  def __ror__(self, other_lens): return Or(self._preprocess_lens(other_lens), self)


  #
  # For overloading
  #

  def _get(self, concrete_input_reader, current_container) :
    """Get proper for a specific lens."""
    raise NotImplementedError("")

  def _put(self, item, concrete_input_reader, current_container) :
    """Put proper for a specific lens."""
    # Note, a low-level lens (i.e. that directly consumes input or tokens)
    # should check if it has been mistakenly passed an item.
    raise NotImplementedError("")


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
    return self.name or str(self)


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
      self.container_get(lens, concrete_input_reader, current_container)

    # Important: we should not return anything, since we work on the outer container!


  def _put(self, item, concrete_input_reader, current_container) :
    
    assert_msg(item == None, "Lens %s did not expect to PUT an individual item %s, since it PUTs from a container" % (self, item))

    # Simply concatenate output from the sub-lenses.
    output = ""
    for lens in self.lenses :
      output += lens.put(None, concrete_input_reader, current_container)

    return output
    

  @staticmethod
  def TESTS() :
    # These tests flex the use of labels.

    d("GET")
    lens = And(AnyOf(alphas, type=str), AnyOf(nums, type=int), type=list)
    got = lens.get("m0nkey")
    assert(got == ["m", 0])
    
    d("PUT")
    got[0] = "d" # Modify an item, though preserving list meta.
    assert(lens.put(got) == "d0")
 
    d("CREATE")
    assert(lens.put(["z", 8]) == "z8")

    d("Input alignment test")
    # Now test alignment of input with a more complex lens
    sub_lens = Group(AnyOf(alphas,type=str) + AnyOf("*+", default="*") + AnyOf(nums, type=int), type=list)
    lens = Group(sub_lens + sub_lens, type=list)
    auto_name_lenses(locals()) 
    got = lens.get("a+3x*6")
    assert(got == [["a", 3], ["x", 6]])

    # Now re-order the items
    got.append(got.pop(0))
    output = lens.put(got)
    # And the non-stored input (i.e. '*' and '+') should have been carried with the abstract items.
    assert(output == "x*6a+3")

    # And for CREATE, using default value for non-store lens.
    output = lens.put([["b",9], ["c", 4]])
    assert(output == "b*9c*4")


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
    
    # Algorithm
    #
    # Try a straight put (i.e. consuming with same lens that puts)
    # Then try cross-put
    #   consume with one lens
    #   put with another, without passing on input reader
    
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

    # Now we must put with one of the lenses, though without passing the (already consumed) input.
    for lens in self.lenses :
      try :
        with automatic_rollback(current_container) :
          return lens.put(item, None, current_container)
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
    # Test straight put
    concrete_input_reader = ConcreteInputReader("abc")
    assert(lens.put("p", concrete_input_reader) == "p" and concrete_input_reader.get_remaining() == "bc")

    # Test cross put
    concrete_input_reader = ConcreteInputReader("abc")
    assert(lens.put(4, concrete_input_reader) == "4" and concrete_input_reader.get_remaining() == "bc")
    
    # d("CREATE")
    # TODO: Need to think of a more complex lens to properly test this vs. put.

    d("Test with default values")
    lens = AnyOf(alphas, type=str) | AnyOf(nums, default=3)
    assert(lens.put() == "3")
    
    # And whilst we are at it, check the outer lens default overrides the inner lens.
    lens.default = "x"
    assert(lens.put() == "x")
    


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
        raise NoDefaultException("Cannot CREATE: a default should have been set on lens %s, or a higher lens." % self)
    
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
    
    lens = AnyOf(alphas, type=str, some_property="some_val")
    assert(lens.options.some_property == "some_val") # Test lens options working.
    
    d("GET")
    got = lens.get("monkey")
    assert(got == "m")

    # Test putting back what we got (i.e. with meta)
    d("PUT")
    assert(lens.put(got) == "m")

    d("CREATE")
    output = lens.put("d")
    assert(output == "d")
   
    d("Test default of non-typed lens is created")
    lens = AnyOf(alphas, default="x")
    output = lens.put()
    assert(output == "x")

    d("Test failure when defalt value required.")
    lens = AnyOf(alphas)
    with assert_raises(NoDefaultException) :
      lens.put()
    
    d("TEST type coercion")
    lens = AnyOf(nums, type=int)
    assert(lens.get("3") == 3)
    assert(lens.put(8) == "8")
    # Check default converted to string.
    lens = AnyOf(nums, default=5)
    assert(lens.put() == "5")
    

class Repeat(Lens) :
  """
  Applies a repetition of the givien lens (i.e. kleene-star).
  """

  def __init__(self, lens, min_count=1, max_count=None, infinity_limit=1000, **kargs):
    super(Repeat, self).__init__(**kargs)
    self.min_count, self.max_count = min_count, max_count
    self.infinity_limit = infinity_limit
    # TODO: Perhaps having an append_sublens in Lens class could ensure
    # coercion always happens.
    self.lenses = [self._coerce_to_lens(lens)]

  def _get(self, concrete_input_reader, current_container) :
    
    # For brevity.
    lens = self.lenses[0]
    
    # Try to get as many as we can, up to a maximum if set.
    no_succeeded = 0
    while(True) :
      try :
        with automatic_rollback(concrete_input_reader, current_container) :
          self.container_get(lens, concrete_input_reader, current_container)
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

    # Algorithm
    #
    # Note, it is tempting first to do GETs then PUTs to simplify this algorithm, though we would
    # loose positional info from input that might be useful in matching up
    # items.
    #
    # First try to put with input - important for potential re-alignment
    # Then try to put with no input
    # Then mop up any remaining input with GET (i.e. if there are fewer abstract items)

    # XXX: This will be made redundant if a container can make the matching choice.
    # To facilitate potential re-alignment of items within the container logic (e.g. perhaps for key
    # matching), this first tries to PUT by passing the outer concrete input (if
    # any) before trying to PUT without (by effectively setting the concrete
    # reader to None).
    effective_concrete_reader = concrete_input_reader
    while True :
      try :
        with automatic_rollback(effective_concrete_reader, current_container) :
          output += self.container_put(lens, effective_concrete_reader, current_container)
          no_succeeded += 1
      except LensException:
        # If we fail and the effective_concrete_reader is set, we may now
        # attempt some PUTs without outer input, by setting the reader to None for the next
        # iteration.
        if has_value(effective_concrete_reader) :
          effective_concrete_reader = None
          continue
        else :
          break

      # Later on, for the GETs to adhere to max_count, we need to know how many
      # were PUT with outer input consumption vs. without.
      if has_value(effective_concrete_reader) :
        no_put = no_succeeded

      # Don't get more than maximim
      if has_value(self.max_count) and no_succeeded == self.max_count :
        break

      # Check for infinite iteration (i.e. if lens does not progress state)
      if has_value(self.infinity_limit) and no_succeeded >= self.infinity_limit :
        raise InfiniteIterationException("Lens may iterate indefinitely - must be redesigned")
    
    # Something with algorthm has gone badly wrong if this fails.
    if has_value(self.max_count) :
      assert(no_succeeded <= self.max_count)

    if no_succeeded < self.min_count :
      raise LensException("Expected at least %s successful GETs" % (self.min_count))
  
   
    # Finally, the items we PUT may be fewer than the number of concrete
    # structures, so we GET and discard as many as required or as possible.
    if has_value(concrete_input_reader) :
      
      # Determine how many we need to get to consume max from input.
      if has_value(self.max_count) :
        no_to_get = self.max_count - no_put
        assert(no_to_get >= 0)
      
      # Do this without get_and_discard to avoid excessive state copying: we
      # only need to make one copy of the original state.
      no_got = 0
      state = get_rollbackables_state(current_container)
      while True :
        try :
          with automatic_rollback(concrete_input_reader) :
            self.container_get(lens, concrete_input_reader, current_container)
            no_got += 1
        except LensException:
          break

        if has_value(self.max_count) and no_got == no_to_get :
          break
      # Now discard any items added by the lens.
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
    # Put as many as were there originally.
    input_reader = ConcreteInputReader("98765")
    assert(lens.put([1,2,3,4,5], input_reader) == "12345" and input_reader.get_remaining() == "")
    
    # Put a maximum (5) of the items (6)
    input_reader = ConcreteInputReader("987654321")
    assert(lens.put([1,2,3,4,5,6], input_reader) == "12345" and input_reader.get_remaining() == "4321")
    
    # Put more than there wereo originally.
    input_reader = ConcreteInputReader("981abc")
    assert(lens.put([1,2,3,4,5,6], input_reader) == "12345" and input_reader.get_remaining() == "abc")
    
    # Put fewer than originally, but consume only max from the input.
    input_reader = ConcreteInputReader("87654321")
    assert(lens.put([1,2,3,4], input_reader) == "1234" and input_reader.get_remaining() == "321")

    d("Test infinity problem")
    lens = Repeat(Empty(), min_count=3, max_count=None, infinity_limit=10)
    with assert_raises(InfiniteIterationException) :
      lens.get("anything")
    with assert_raises(InfiniteIterationException) :
      lens.put(None)
    
    d("Test non-typed lenses.")
    lens = Repeat(AnyOf(nums))
    input_reader = ConcreteInputReader("12345abc")
    d(lens.get(input_reader) == None and input_reader.get_remaining() == "abc")
    input_reader.reset()
    # Lens should make use of outer input, since not supplied by an item.
    assert(lens.put(None, input_reader, None) == "12345" and input_reader.get_remaining() == "abc")

    d("Test the functionality without default values.")
    # Should fail, since lens has no default
    with assert_raises(LensException) :
      lens.put()

    d("Test the functionality with default value on Repeat.")
    lens = Repeat(AnyOf(nums), default="54321")
    assert(lens.put() == "54321")
    
    d("Test the functionality with default value on sub-lens.")
    lens = Repeat(AnyOf(nums, default=4), infinity_limit=10)
    # This will give us: "44444444444444444......"
    with assert_raises(InfiniteIterationException) :
      lens.put()

    d("Test putting back what we got (i.e. with source meta)")
    lens = Repeat(AnyOf(nums, type=int), type=list)
    assert(lens.put(lens.get("1234")) == "1234")




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

    # Note that, useless as it is, this is actually an item that could potentially be stored that we
    # return, which is why we must explicitly check for None elsewhere in the
    # framework, since "" == False but "" != None.
    if self.has_type() :
      return ""
    return None

  def _put(self, item, concrete_input_reader, current_container) :
    
    # We should not be passed an item with we are a non-store lens.
    if not self.has_type() and has_value(item) :
      raise LensException("Did not expect to be passed an item")

    # Here we can put only the empty string token, though if this lens does not
    # store an item, the default value of "" will intercept this function being called.
    if not (isinstance(item, str) and item == "") :
      raise LensException("Expected to put an empty string")
    return ""

  @staticmethod
  def TESTS() :
    
    d("Test with type")
    lens = Empty(type=str)
    assert(lens.get("anything") == "")
    assert(lens.put("", "anything") == "")
    with assert_raises(LensException) :
      lens.put(" ", "anything")
    
    assert(lens.put("") == "")


    d("Test without type")
    lens = Empty()
    assert lens.get("anything") == None 
    assert lens.put() == ""
    # Lens does not expect to put an item, valid or otherwise.
    with assert_raises(LensException) :
      lens.put("", "anything")
 
    d("Test special modes.")
    lens = Empty(mode=Empty.START_OF_TEXT)
    concrete_reader = ConcreteInputReader("hello")
    # Progress the input reader so lens does not match.
    concrete_reader.get_next_char()
    with assert_raises(LensException) : 
      lens.get(concrete_reader)
    
    lens = Empty(mode=Empty.END_OF_TEXT)
    concrete_reader = ConcreteInputReader("h")
    # This should throw an Exception
    with assert_raises(LensException) : 
      lens.get(concrete_reader)
    concrete_reader.get_next_char()
    # This should succeed quietly.
    lens.get(concrete_reader)



class Group(Lens) :
  """
  A convenience lens that thinly wraps any lens to set a type.
  """

  def __init__(self, lens, **kargs):
    super(Group, self).__init__(**kargs)
    assert_msg(self.has_type(), "To be meaningful, you must set a type on %s" % self)
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

    d("TEST untyped Group")
    with assert_raises(AssertionError) :
      lens = Group(AnyOf(nums))
