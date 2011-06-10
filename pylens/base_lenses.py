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

"""Contains base lenses, from which all other lenses are derived."""

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
  """Base lens, which handles most of the complexity."""
  
  def __init__(self, type=None, name=None, default=None, **kargs) :
    # Set python type of this lens.  If a lens has a type it is effectively a
    # STORE lens, as described in the literature.
    self.type = type

    # Set the default value of this lens (in the PUT direction) if it is not a
    # STORE lens.
    if has_value(type) and has_value(default) :
      raise Exception("Cannot set a default value on a lens with a type (i.e. on a store lens).")
    self.default = default
    
    # For debugging purposes, allow a friendly name to be given to the lens,
    # otherwise an automated name will be displayed (e.g. "And(106)")
    self.name = name

    # Composite lenses will store their sub-lenses in here, for consistency,
    # and later perhaps to allow for some reasonning about a lens' structure.
    self.lenses = []

    # Allow arbitrary arguments to be set on the lens which can aid flexible
    # storage and retrival of items from a container.
    self.options = Properties(kargs)

    #
    # Argument shortcuts
    #

    # There is no point setting a non-store lens as a label or to have a
    # label, so assume the user wanted a lens type of str.
    if not has_value(self.type) and (self.options.is_label or self.options.label) :
      self.type = str



  def get(self, concrete_input, current_container=None) :
    """
    The top-level API function to extract a python structure from a given
    string with this lens.

    Arguments:
      concrete_input - concrete string or stateful concrete input reader
      current_container - outer container into which items are being extracted

    This effectively wraps the _get function (GET proper) of the specific
    lens, handling all of the common tasks (e.g. input normalisation, creation
    of stateful containers, rolling back state for failed parsing branches).
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

    # Ensure we have the concrete input in the form of a ConcreteInputReader
    assert_msg(has_value(concrete_input), "Cannot GET if there is no input string!")
    concrete_input_reader = self._normalise_concrete_input(concrete_input)
  
    if IN_DEBUG_MODE :
      d("Initial state: in={concrete_input_reader}, cont={current_container}".format(
        concrete_input_reader = concrete_input_reader,
        current_container = current_container,
      ))

    # Remember the start position of the concrete reader, to aid
    # re-alignment of concrete structures when we Lens.put is later called.
    # We will store this in a returned items meta_data, effictively giving it
    # a lifeline back to where it came from.
    concrete_start_position = concrete_input_reader.get_pos()

    # Create an empty appropriate container class for our lens, if there is one;
    # this will be None if we are not a container-type lens (e.g. a dict or
    # list).
    new_container = self._create_container()

    # If we are a container-type lens, replace the current container of
    # sub-lenses with our own container (new_container).
    if new_container :
      # Call GET proper with our container, checking that no item is returned,
      # since all items should be stored WITHIN the container
      assert_msg(self._get(concrete_input_reader, new_container) == None, "Container lens %s has GOT an item, but all items must be stored in the current container, not returned." % self)
      
      # Since we created the container, we will return it as our item, for a
      # higher order lens to store.
      item = new_container.unwrap()
    # Otherwise, call GET proper using the outer container, if there is one.
    else :
      item = self._get(concrete_input_reader, current_container)

    # If we are a STORE lens (i.e. we extract an item) ...
    if self.has_type() :
      
      # Cast the item to our type (usually if it is a string being cast to a
      # simple type, such as int).
      assert_msg(has_value(item), "Somethings gone wrong: %s is a STORE lens, so we should have got an item." % self)
      if not isinstance(item, self.type) :
        item = self.type(item)

      # Double check we got an item of the correct type (after any casting).
      assert(isinstance(item, self.type))
     
      # Allow meta data to be stored on the item.
      item = enable_meta_data(item)
      
      # Now add source info to the item's meta data, which will help when
      # putting it back into a concrete structure.
      
      # A refernce to the lens that extracted the item.
      item._meta_data.lens = self

      # A reference to the concrete reader and position parsed from.
      item._meta_data.concrete_start_position = concrete_start_position
      item._meta_data.concrete_input_reader = concrete_input_reader

    # Note that, even if we are not a typed lens, we may return an item
    # extracted from some sub-lens, the Or lens being a good example.

    if IN_DEBUG_MODE :
      if has_value(item) :
        d("GOT: %s %s" % (item, item._meta_data.label and "[label: '%s']" % (item._meta_data.label) or ""))
      else :
        d("GOT: NOTHING")
    
    # Pre-process outgoing item.
    item = self._process_outgoing_item(item)

    return item


  def put(self, item=None, concrete_input=None, current_container=None, label=None) :
    """
    The top-level API function to PUT a python structure back into a string
    structure.  This function holds much of the framework's complexity.

    Arguments:
      item - item to PUT back.
      concrete_input - concrete input for weaving between STORE lens values
      current_container - outer container from which items will be consumed
      and PUT back
      label - allows the user to set a label on the passed item, to allow for
      structures that internally contain a label.

    This effectively wraps the _put function (PUT proper) of the specific
    lens, handling all of the common tasks (e.g. input normalisation, creation
    of stateful containers, rolling back state for failed parsing branches).

    Note that we make no distinction between PUT and CREATE (from the
    literatur): since a previously extracted item will carry information of
    its concrete structure within its meta data it will use this for weaving
    in non-stored artifacts; otherwise, default artifacts will be used (as in
    CREATE).

    In some cases the order that items are put back in will differ from their
    original order, so we are careful to both consume and discard from the
    outer concrete structure whislt PUTing with the item' own concrete
    structure.  If both structures are aligned (i.e. the item goes back in its
    original order) then a single PUT on the outer concrete reader is
    performed.
    """
   
    #
    # Algorithm
    #
    # Assert item => container == None
    # Note, though an item will hold its own input, the lens must consumed from
    # the outer input reader if one is supplied.
    #
    # Normalise concrete input reader.
    #
    # If we are an un-typed lens
    #   if we have a default value and no concrete input, return it.
    #   otherwise return put proper, passing through our args - note, item could be passed through us
    #
    # Now assume we are typed lens
    #
    #  If we are passed an item
    #    ensure meta enabled (e.g. for a new item, not previously extracted)
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
      # Note, however, that a typed item may well be passed an outer concrete
      # reader, which will be used for weaving in non-stored artifacts of concrete
      # structures.

    # Ensure we have a ConcreteInputReader; otherwise None.
    concrete_input_reader = self._normalise_concrete_input(concrete_input)

    if IN_DEBUG_MODE :
      
      # It's very useful to see if an item holds a label in its meta.
      if hasattr(item, "_meta_data") and has_value(item._meta_data.label) :
        item_label_string = " [label: %s]" % item._meta_data.label
      else :
        item_label_string = ""
      
      d("Initial state: item={item}{item_label_string}, in={concrete_input_reader}, cont={current_container}".format(
        item = item,
        concrete_input_reader = concrete_input_reader,
        current_container = current_container,
        item_label_string = item_label_string,
      ))

    # Handle cases where our lens does not directly store an item.
    if not self.has_type() :
      
      # Use default (for CREATE)
      if concrete_input_reader == None and has_value(self.default) :
        # XXX: Note sure about this - need to think about the more general
        # problem.
        #if has_value(item):
        #  raise LensException("%s should definitely not have been passed an item '%s' since a non-store lens with a default." % (self, item))
        return str(self.default)
      
      # Otherwise do a PUT proper, passing through our arguments, for example
      # our child lens may put an item directly or from the container of use
      # its own default value.
      output = self._put(item, concrete_input_reader, current_container)
      d("PUT: '%s'" % output or "NOTHING")
      return output


    # Now we can assume that our lens has a type (i.e. will directly PUT an
    # item)
    if has_value(item) :
    
      # For the sake of algorithmic consistancy, ensure the incoming item can
      # hold meta data.
      item = enable_meta_data(item)
      
      # Associate a label with the item, usually a label passed from the user
      # which is required internally by a structure.
      if has_value(label) :
        item._meta_data.label = label

      # Pre-process the incoming item (e.g to handle auto_list)
      item = self._process_incoming_item(item)
     
      # Check our item's type is compatible with the lens.
      if not isinstance(item, self.type) :
        raise LensException("This lens %s of type %s cannot PUT an item of that type %s" % (self, self.type, type(item)))
      
      # If this item was previously GOTten, we can get its original input.
      if item._meta_data.concrete_input_reader :
        
        # Create a personal concrete reader for this item, based on its meta
        # data.
        item_input_reader = ConcreteInputReader(item._meta_data.concrete_input_reader)
        item_input_reader.set_pos(item._meta_data.concrete_start_position)

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
        
        # Otherwise, if our item had no source meta, we will be CREATING, but
        # must still consume from the outer reader, if there is one.
        if has_value(concrete_input_reader) :
          d("Inputs not aligned, so consuming and discarding from outer input reader.")
          self.get_and_discard(concrete_input_reader, current_container)
        
        concrete_input_reader = None
      
      # Now, the item could be a container (e.g. a list, dict, or some other
      # AbstractContainer), so to save the _put definition from having to wrap
      # it for stateful consumption of items, let's do it here.
     
      # TODO: We need to check that the container, if from an item, has been fully consumed
      # here and raise an LensException if it has not.
      item_as_container = ContainerFactory.wrap_container(item, container_lens=self)
      if item_as_container :
        # The item is now represented as a consumable container.
        item = None
        current_container = item_as_container
      else :
        # When PUTing a non-container item, for consistancy, should cast to string (e.g. if int
        # passed) and discard current container from this branch.
        item = str(item)
        current_container = None

      # Now that arguments are set up, call PUT proper on our lens.
      output = self._put(item, concrete_input_reader, current_container)
      d("PUT: '%s'" % output or "NOTHING")
      return output
   
    # If instead of an item we have a container, instruct the container to put
    # an item into the lens.  This gives the container much flexibilty about
    # how it chooses an item to PUT, perhaps even doing so tentatively.
    elif has_value(current_container) :
      assert(isinstance(current_container, AbstractContainer))
      output = current_container.consume_and_put_item(self, concrete_input_reader)
      d("PUT: '%s'" % output or "NOTHING")
      return output

    # We should have returned by now.
    raise LensException("This typed lens expected to PUT an item either directly or from a container.")


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


  def container_get(self, lens, concrete_input_reader, current_container) :
    """
    Convenience function to handle the case where:
      - if there is a container, get and store an item into it
      - if there is no container, call get and check nothing is returned
    
    This simplifies lens such as And and Repeat, whose logic does not have to
    worry about whether or not it is acting as a STORE lens.
    """
    if has_value(current_container) :
      current_container.get_and_store_item(lens, concrete_input_reader)
    else :
      # Call get on lens passing no container, checking it returns no item.
      assert_msg(lens.get(concrete_input_reader, None) == None,
        "The untyped container lens %s did not expect the sub-lens %s to return an item" % (self, lens)
      )

  def container_put(self, lens, concrete_input_reader, current_container) :
    """Reciprocal of container_get."""
    if lens.has_type() :
      assert_msg(has_value(current_container), "Lens %s expected an enclosing container from which to pluck an item." % lens)
      return current_container.consume_and_put_item(lens, concrete_input_reader)
    else :
      # Otherwise, we pass through arguments (e.g. for non-store sublenses or
      # lens that enclose STORE lenses)
      return lens.put(None, concrete_input_reader, current_container)

  def set_sublens(self, sublens) :
    """Used if only a single sublens is required (e.g. the Forward lens)."""
    self.lenses = [self._preprocess_lens(sublens)]

  def extend_sublenses(self, new_sublenses) :
    """
    Adds new sublenses to this lens, being sure to preprocess them (e.g. convert
    strings to Literal lenses, etc.).
    """
    for new_sublens in new_sublenses :
      self.lenses.append(self._preprocess_lens(new_sublens))

  #
  # Helper methods.
  #

  def _normalise_concrete_input(self, concrete_input) :
    """If a string is passed, ensure it is normalised to a ConcreteInputReader."""
    if not has_value(concrete_input) :
      return None
    
    if isinstance(concrete_input, str) :
      concrete_input = ConcreteInputReader(concrete_input)
   
    assert_msg(isinstance(concrete_input, ConcreteInputReader), "Expected to have a ConcreteInputReader not a %s" % type(concrete_input))
    return concrete_input

  def _create_container(self):
    """Creates a container for this lens, if the lens is of a container type."""
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
    
    assert_msg(isinstance(lens_operand, Lens), "Unable to coerce %s to a lens" % lens_operand)
    return lens_operand

  def _preprocess_lens(self, lens) :
    """
    Preprocesses a lens to enable type-to-lens conversion. This will be
    called before processing lens arguments.
    """
    lens = Lens._coerce_to_lens(lens)
    return lens


  #
  # Allow the potential modification of incoming and outgoing items (e.g. to
  # handle auto_list, where a single-item list is converted to and from a
  # single item)
  #

  def _process_outgoing_item(self, item) :
    """
    Allows post-processing of an item in the GET direction.
    
    For example, to handle auto_list, where a single-item list is converted to
    a single item.
    """
    
    # This allows a list singleton to be returned as a single item, for
    # convenience.
    if self.options.auto_list == True and self.has_type() and issubclass(self.type, list) and len(item) == 1:
      # The easy part is extracting a singleton from the list, but we must
      # also preserve the source meta data of the list item by piggybacking it onto
      # the extracted item's meta data

      list_meta_data = item._meta_data
      singleton_meta_data = item[0]._meta_data
      item = item[0]
      item._meta_data = list_meta_data
      item._meta_data.singleton_meta_data = singleton_meta_data
    
    # This allows a list of chars to be combined into a string.
    elif self.options.combine_chars and self.has_type() and issubclass(self.type, list):
      # Note, care should be taken to use this only when a list of single chars is used.
      # XXX: Note, we actually loose each char's meta data here, but this should not be a problem in most cases.
      original_meta = item._meta_data
      item = enable_meta_data("".join(item))
      item._meta_data = original_meta
      
    return item


  def _process_incoming_item(self, item) :
    """
    Pre-processes an item in the PUT direction. 
    
    For example, reciprocating the auto_list example in
    _process_outgoing_item.
    """
    
    # Handle auto_list, expanding an item into a list, being careful to restore any meta data.
    if self.options.auto_list == True and self.has_type() and issubclass(self.type, list) and not isinstance(item, list):

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

    # This allows a list of chars to be combined into a string.
    elif isinstance(item, str) and self.options.combine_chars and self.has_type() and issubclass(self.type, list):
      # Note, care should be taken to use this only when a list of single chars is used.
      original_meta = item._meta_data
      item = enable_meta_data(list(item))
      item._meta_data = original_meta

    return item


  #
  # Operator overloads to make for cleaner lens construction.
  #
  
  def __add__(self, other_lens): return And(self, self._preprocess_lens(other_lens))
  def __or__(self, other_lens): return Or(self, self._preprocess_lens(other_lens))

  # Reflected operators, so we can write: lens = "a string" + <some_lens>
  def __radd__(self, other_lens): return And(self._preprocess_lens(other_lens), self)
  def __ror__(self, other_lens): return Or(self._preprocess_lens(other_lens), self)


  #
  # Specialised lenses must override these to implement their GET and PUT
  # proper.
  #

  def _get(self, concrete_input_reader, current_container) :
    """GET proper for a specific lens."""
    raise NotImplementedError("")

  def _put(self, item, concrete_input_reader, current_container) :
    """
    PUT proper for a specific lens.
    
    Note, a low-level lens (i.e. that directly consumes input or tokens)
    should check if it has been mistakenly passed an item to PUT if it is not
    operating as a STORE lens (i.e. if the lens has no type).
    """
    raise NotImplementedError("")


  #
  # For debugging
  #
  
  def _display_id(self) :
    """Useful for identifying specific lenses in debug traces."""
    # If we have a specic name, use it.
    if self.name :
      return self.name

    # If no name, a hash with small range gives us a reasonably easy way to
    # distinguish lenses in debug traces.
    return str(hash(self) % 256)

  # String representation.
  def __str__(self) :
    # Bolt on the class name, to ease debugging.
    return "%s(%s)" % (self.__class__.__name__, self._display_id())
  __repr__ = __str__

  def __instance_name__(self) :
    """Used by my nbdebug module to display a custom debug message context string."""
    return self.name or str(self)



#########################################################
# Core lenses - required fundamental lenses.
#########################################################
    
class And(Lens) :
  """A lens that is formed from the ANDing of two sub-lenses."""

  def __init__(self, *lenses, **kargs):
   
    # Must always remember to invoke the parent lens, so it can initialise
    # common arguments.
    super(And, self).__init__(**kargs)

    # Flatten sub-lenses that are also Ands, so we don't have too much nesting,
    # which makes debugging lenses a nightmare.
    for lens in lenses :
      # Note, isinstance would be too vague - Word() was absorbed due to this.
      if lens.__class__ == self.__class__ :
        self.extend_sublenses(lens.lenses)
      else :
        self.extend_sublenses([lens])


  def _get(self, concrete_input_reader, current_container) :
    """Sequential GET on each lens."""
    for lens in self.lenses :
      self.container_get(lens, concrete_input_reader, current_container)

    # Important: we should not return anything, since we work on the outer
    # container, that the Lens class sets up for us in Lens.get regardless if our
    # lens created the container or not.


  def _put(self, item, concrete_input_reader, current_container) :
    """Sequential PUT on each lens."""
    # In the same way that we do not return an item in GET, we do not expect
    # to PUT an individual item; again, this is handle in Lens.put
    assert_msg(item == None, "Lens %s did not expect to PUT an individual item %s, since it PUTs from a container" % (self, item))

    # Simply concatenate output from the sub-lenses.
    output = ""
    for lens in self.lenses :
      output += lens.put(None, concrete_input_reader, current_container)

    return output
    

  @staticmethod
  def TESTS() :
    d("GET")
    lens = And(AnyOf(alphas, type=str), AnyOf(nums, type=int), type=list)
    got = lens.get("m0nkey")
    assert(got == ["m", 0])
    
    d("PUT")
    got[0] = "d" # Modify an item, though preserving list source info in meta.
    assert(lens.put(got) == "d0")
 
    d("CREATE") # The new list and items will hold no meta.
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
  """
  
  def __init__(self, *lenses, **kargs):
    super(Or, self).__init__(**kargs)

    # Flatten sub-lenses that are also Ors, so we don't have too much nesting, which makes debugging lenses a nightmare.
    for lens in lenses :
      # Note, isinstance would be too vague - see my note in And.
      if lens.__class__ == self.__class__ :
        self.extend_sublenses(lens.lenses)
      else :
        self.extend_sublenses([lens])


  def _get(self, concrete_input_reader, current_container) :
    """
    Calls get on each lens until the firstmost succeeds.
    
    Note that the lens should be designed accordingly to break ties over
    multiple valid paths.
    """
    for lens in self.lenses :
      try :
        with automatic_rollback(concrete_input_reader, current_container) :
          return lens.get(concrete_input_reader, current_container)
      except LensException:
        pass
        
    raise LensException("We should have GOT one of the lenses.")

  def _put(self, item, concrete_input_reader, current_container) :
    """
    It is important to realise that here we can either do a:
      - straight PUT, where the lens both consumes input and PUTs an item
      - cross PUT, where one lens consumes input and another PUTS an item

    Also, it is useful to consider a lens l = A | Empty(), since if we first try
    straight PUT with each lens, the Empty lens will always succeed, possibly
    resulting in input not being consumed correctly by lens A.  This case
    influences my redesign of this algorithm.
    """

    # Algorithm
    #
    # For lens_a in lenses
    #   Try straight put with lens_a -> return if succeed
    #   lens_a.get_and_discard(input)
    #
    #   For lens_b in lenses, lens_b != lens_a
    #     lens.put(input=None)

    # Store the initial state.
    initial_state = get_rollbackables_state(concrete_input_reader, current_container)

    for lens_a in self.lenses:
      # Try a straight put on the lens - this will also succeed if there is no
      # input.
      try :
        with automatic_rollback(concrete_input_reader, current_container, initial_state=initial_state) :
          return lens_a.put(item, concrete_input_reader, current_container)
      except LensException:
        pass
     
      # If we have a concrete_input_reader, we will next attempt a cross PUT.
      if not concrete_input_reader :
        continue

        
      # Try to consume input with the lens_a
      try :
        with automatic_rollback(concrete_input_reader, current_container, initial_state=initial_state) :
          lens_a.get_and_discard(concrete_input_reader, current_container)
      except LensException:
        continue

      # If the GET suceeded with lens_a, try to PUT with one of the other
      # lenses.
      for lens_b in self.lenses:
        if lens_a is lens_b:
          continue

        try :
          with automatic_rollback(concrete_input_reader, current_container, initial_state=initial_state) :
            return lens_b.put(item, None, current_container)
        except LensException:
          pass



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
    assert(lens.put(4, concrete_input_reader) == "4")
    assert(concrete_input_reader.get_remaining() == "bc")
    
    d("Test with default values")
    lens = AnyOf(alphas, type=str) | AnyOf(nums, default=3)
    assert(lens.put() == "3")
    assert(lens.put("r") == "r")
    
    # And whilst we are at it, check the outer lens default overrides the inner lens.
    lens.default = "x"
    assert(lens.put() == "x")

    d("Test sensible handling of Empty lens.")
    # Actually, this issue (if not fixed) will manifest only if we use container.
    lens = AnyOf(alphas, type=str) | Empty()
    concrete_input_reader = ConcreteInputReader("b4")
    assert(lens.put("4", concrete_input_reader) == "" and concrete_input_reader.get_remaining() == "4")

    d("Test sensible handling of Empty lens with container.")
    lens = Group((AnyOf(alphas, type=str) | Empty()) + AnyOf(nums, type=int), type=list)
    concrete_input_reader = ConcreteInputReader("a4")
    got = lens.get(concrete_input_reader)
    assert(got == ["a", 4])
    
    # We expect that: put char that is not in alphas, so Empty used, yet full string consumed.
    # This is an important test that OR works as expected (i.e. according to the
    # ordering of operand lenses) with a lens such as
    # Empty()
    concrete_input_reader.reset()
    del got[0] # Important that we use 'got' so input is aligned.
    assert(lens.put(got, concrete_input_reader) == "4")
    assert(concrete_input_reader.is_fully_consumed())
    

    


class AnyOf(Lens) :
  """
  The first useful low-level lens. Matches a single char within a specified
  set, and can also be negated.
  """
  
  def __init__(self, valid_chars, negate=False, **kargs):
    super(AnyOf, self).__init__(**kargs)
    self.valid_chars, self.negate = valid_chars, negate
 
  def _get(self, concrete_input_reader, current_container) :
    """
    Consumes a valid char from the input, returning it if we are a STORE
    lens.
    """
    char = None
    try:
      char = concrete_input_reader.consume_char()
      if not self._is_valid_char(char) :
        raise LensException("Expected char %s but got '%s'" % (self._display_id(), truncate(char)))
    except EndOfStringException:
      raise LensException("Expected char %s but at end of string" % (self._display_id()))
   
    if self.has_type() :
      return char
    else :
      return None


  def _put(self, item, concrete_input_reader, current_container) :
    """
    If a store lens, tries to output the given char; otherwise outputs
    original char from concrete input.
    """
    # If we are not a store lens, simply return what we would consume from the input.
    if not self.has_type() :
      # We should not have been passed an item.
      assert(not has_value(item))
      if has_value(concrete_input_reader) :
        concrete_start_position = concrete_input_reader.get_pos()
        self._get(concrete_input_reader, current_container)
        return concrete_input_reader.get_consumed_string(concrete_start_position)
        
      else :
        raise NoDefaultException("Cannot CREATE: a default should have been set on lens %s, or a higher lens." % self)
    
    # If this is PUT (vs CREATE) then first consume input.
    if concrete_input_reader :
      self.get(concrete_input_reader)
    
    
    if not (isinstance(item, str) and len(item) == 1 and self._is_valid_char(item)) :
      raise LensException("Invalid item '%s', expected %s." % (item, self._display_id()))
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
    assert(lens.options.some_property == "some_val") # Might as well test lens options working.
    
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

    d("Test failure when default value required.")
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

  # XXX: infinity_limit will be deprecated.
  def __init__(self, lens, min_count=1, max_count=None, infinity_limit=1000, **kargs):
    """
    Arguments:
      lens - the lens to repeat
      min_count - the min repetitions
      max_count - maximum repetitions (must be > 0 if set)
      infinity_limit - For the sake of simplicity, rather than trying to
      determine if a grammar may repeat infinitely (e.g. Repeat(Empty()).get()
      being a simple example) we allow a looping limit to be set, with the aim
      of signalling that a lens should be redesigned.
    """
    super(Repeat, self).__init__(**kargs)
    assert(min_count >= 0)
    if has_value(max_count) :
      assert(max_count > min_count)
      assert(infinity_limit > max_count)
    
    self.min_count, self.max_count = min_count, max_count
    self.infinity_limit = infinity_limit
    self.extend_sublenses([lens])


  def _get(self, concrete_input_reader, current_container) :
    """Calls a sequence of GETs on the sub-lens."""

    # Algorithm
    #
    # Loop until max count reached or lens fails to alter input state (which
    # could happen indefinitely.

    # For brevity.
    lens = self.lenses[0]
   
    # For tracking how many successful GETs
    no_got = 0

    while(True) :
      # Instantiate the rollback context, so we can later check if any state was changed.
      rollback_context = automatic_rollback(concrete_input_reader, current_container, check_for_state_change=True)
      try :
        with rollback_context :
          self.container_get(lens, concrete_input_reader, current_container)
        
        # If the lens changed no state, then we must break, otherwise continue
        # for ever.
        if not rollback_context.some_state_changed :
          d("Lens %s changed no state during this iteration, so we must break out - or spin for ever" % lens)
          break
        
        no_got += 1

        # Don't get more than maximim
        if has_value(self.max_count) and no_got == self.max_count :
          break
      except LensException :
        break

    if no_got < self.min_count :
      raise TooFewIterationsException("Expected at least %s successful GETs but got only %s" % (self.min_count, no_got))
    

  def _put(self, item, concrete_input_reader, current_container) :
    """Calls a sequence of PUTs on the sub-lens."""

    # Algorithm
    #
    # - First we try to PUT with the lenses (first using input if it is available)
    # - Then, we must check that the minumum items have been consumed from input:
    # we may have PUT all new items (i.e. without input consumption) so still
    # need to call GET for a minimum number of times.
    # - In both cases we must break out if a lens changes no state.

    # For brevity.
    lens = self.lenses[0]

    no_got = 0    # For checking how many items of input were consumed
    no_put = 0    # For checking how many items were PUT.
    output = ""

    # This simplifies our algorithm.
    if concrete_input_reader :
      input_readers = [concrete_input_reader, None]
    else :
      input_readers = [None]

    #
    # Handle the PUT/CREATEs
    #

    for input_reader in input_readers :
      
      # Allows a higher level break from within the while loop.
      break_for_loop = False

      while True :
        # Call PUT on the lens and break this while loop if no state changed or we
        # get a LensException.  Also, break the for loop if we PUT max count.
        rollback_context = automatic_rollback(input_reader, current_container, check_for_state_change=True)
        try :
          with rollback_context:
            put = self.container_put(lens, input_reader, current_container)
        except LensException:
          break

        if not rollback_context.some_state_changed :
          d("Lens %s changed no state during this iteration, so we must break out - or spin for ever" % lens)
          break

        output += put
        no_put += 1
        
        # If the succeeded when we used an input reader, we must have consumed
        # input with the lens.
        if has_value(input_reader) :
          no_got += 1

        # We have PUT enough items now.
        if no_put == self.max_count :
          d("We have put enough items now, so breaking out.")
          break_for_loop = True
          break
      
      if break_for_loop :
        break

    
    #
    # Now consume and discard input if necessary.
    #

    # TODO
    # can also add an assertion, since if put min, should have got min also.
    if concrete_input_reader and no_got < self.max_count:
      while(True) :
        # Instantiate the rollback context, so we can later check if any state was changed.
        # Don't need to rollback container, since get_and_discard will do that.
        rollback_context = automatic_rollback(concrete_input_reader, check_for_state_change=True)
        try :
          with rollback_context :
            # XXX: Wasteful to keep getting start state, can prolly store initial state before loop.
            lens.get_and_discard(concrete_input_reader, current_container)
          
          # If the lens changed no state, then we must break, otherwise continue
          # for ever.
          if not rollback_context.some_state_changed :
            d("Lens %s changed no state during this iteration, so we must break out - or spin for ever" % lens)
            break
          
          no_got += 1

          # Don't get more than maximim
          if has_value(self.max_count) and no_got == self.max_count :
            break
        except LensException :
          break


    if no_put < self.min_count :
      raise TooFewIterationsException("Expected at least %s successful PUTs but put only %s" % (self.min_count, no_put))
   
    # Should try to consume max from input.
    #assert(no_got >= self.min_count)

    return output

    no_succeeded = 0
    no_put = 0

    # Algorithm
    #
    # Note, it is tempting first to do GETs then PUTs to simplify this algorithm, though we would
    # loose positional info from input that might be useful in matching up
    # items.
    #
    # - Firstly, try to PUT as many items as we have, trying first with input
    # (for LABEL alignment, which is yet to be implemented) then without input.
    # Then mop up any remaining input with GET (i.e. if there are fewer abstract items)

    # To facilitate potential re-alignment of items within the container logic (e.g. perhaps for key
    # matching), this first tries to PUT by passing the outer concrete input (if
    # any) before trying to PUT without (by effectively setting the concrete
    # reader to None).
    effective_concrete_reader = concrete_input_reader
    while True :
      # Instantiate the rollback context, so we can later check if any state was changed.
      rollback_context = automatic_rollback(effective_concrete_reader, current_container, check_for_state_change=True)
      do_check = True
      try :
        with rollback_context:
        #  with automatic_rollback(effective_concrete_reader, current_container) :
          output += self.container_put(lens, effective_concrete_reader, current_container)
          no_succeeded += 1
      except LensException:
        # If we fail and the effective_concrete_reader is set, we may now
        # attempt some PUTs without outer input, by setting the reader to None for the next
        # iteration.
        if has_value(effective_concrete_reader) :
          # XXX: Note, this is not actually flexed in the tests, but will be
          # when we add LABEL alignment.
          effective_concrete_reader = None
          do_check = False
          continue
        else :
          # XXX: WORKING HERE!
          # XXX: Hmmm, need to think about when we expect something to be
          # consumed inspite of the effective_concrete_reader idea.
          break

      # Break out if no state changed (input or container state)
      if do_check and not rollback_context.some_state_changed :
        raise InfiniteIterationException("Lens may iterate indefinitely - must be redesigned")
      
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
      # only need to make one copy of the original container state.
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
   
    # Note, for some of these tests we need to ensure we PUT rather than CREATE
    # the lists so we can flex the code when input is aligned.

    lens = Repeat(AnyOf(nums, type=int), min_count=3, max_count=5, type=list)
    d("GET")
    assert(lens.get("1234") == [1,2,3,4])
    with assert_raises(TooFewIterationsException) :
      lens.get("12")
    # Test max_count
    assert(lens.get("12345678") == [1,2,3,4,5])

    d("PUT")
    # Put as many as were there originally.
    input_reader = ConcreteInputReader("98765")
    assert(lens.put([1,2,3,4,5], input_reader) == "12345" and input_reader.get_remaining() == "")
    
    # Put a maximum (5) of the items (6)
    input_reader = ConcreteInputReader("987654321")
    assert(lens.put([1,2,3,4,5,6], input_reader) == "12345" and input_reader.get_remaining() == "4321")
    
    test_description("Put more than there were originally.")
    input_reader = ConcreteInputReader("981abc")
    got = lens.get(input_reader)
    got.insert(2, 3)
    input_reader.reset()
    assert(lens.put(got, input_reader) == "9831" and input_reader.get_remaining() == "abc")


    test_description("PUT fewer than got originally, but consume only max from the input.")
    input_reader = ConcreteInputReader("87654321")
    got = lens.get(input_reader)
    del got[2]   # Remove the 6
    input_reader.reset()
    assert(lens.put(got, input_reader) == "8754")
    assert(input_reader.get_remaining() == "321")

    test_description("Test non-typed lenses.")
    lens = Repeat(AnyOf(nums))
    input_reader = ConcreteInputReader("12345abc")
    d(lens.get(input_reader) == None and input_reader.get_remaining() == "abc")
    input_reader.reset()
    # Lens should make use of outer input, since not supplied by an item.
    assert(lens.put(None, input_reader, None) == "12345" and input_reader.get_remaining() == "abc")

    test_description("Test the functionality without default values.")
    # Should fail, since lens has no default
    with assert_raises(LensException) :
      lens.put()

    test_description("Test the functionality with default value on Repeat.")
    lens = Repeat(AnyOf(nums), default="54321")
    assert(lens.put() == "54321")
    

    d("Test putting back what we got (i.e. with source meta)")
    lens = Repeat(AnyOf(nums, type=int), type=list)
    assert(lens.put(lens.get("1234")) == "1234")

    d("Test for completeness")
    lens = Repeat(AnyOf(nums, type=int), type=list, min_count=0, max_count=1)
    assert(lens.get("abc") == []) # No exception thrown since min_count == 0
    assert(lens.get("123abc") == [1])
    assert(lens.put([1,2,3]) == "1")


    d("Test combine_chars")
    lens = Repeat(AnyOf(alphas, type=str), type=list, combine_chars=True)
    assert(lens.get("abc123") == "abc")
    assert(lens.put("xyz") == "xyz")

    #
    # Infinite looping tests
    #

    #d("Test infinity problem")
    #lens = Repeat(Empty(), min_count=3, max_count=None, infinity_limit=10)
    #got = lens.get("")
    
    #return

    d("Test infinity problem")
    lens = Repeat(Empty(), min_count=3, max_count=None, infinity_limit=10)
    # Will fail to get anything since Empty lens changes no state.
    with assert_raises(LensException) :
      lens.get("anything")
    # Likewise.
    with assert_raises(LensException) :
      lens.put(None)
    
    d("Test the functionality with default value on sub-lens.")
    lens = Repeat(AnyOf(nums, default=4), infinity_limit=10)
    # Should faile since no input or items are consumed by the lens.
    with assert_raises(LensException) :
      lens.put()

class Empty(Lens) :
  """
  Matches the empty string, used by Optional().  Can also set modes for special
  empty matches (e.g. at the start or end of a string).
  """
  
  # Useful modifiers for empty matches.
  START_OF_TEXT = "START_OF_TEXT"
  END_OF_TEXT   = "END_OF_TEXT"

  def __init__(self, mode=None, **kargs):
    super(Empty, self).__init__(**kargs)
    self.default = ""
    self.mode = mode


  def _get(self, concrete_input_reader, current_container) :
    
    # Check for special modes.
    if self.mode == self.START_OF_TEXT :
      if concrete_input_reader.get_pos() != 0 :
        raise LensException("Will match only at start of text.")
    elif self.mode == self.END_OF_TEXT :
      if not concrete_input_reader.is_fully_consumed() :
        raise LensException("Will match only at end of text.")

    # Note that, useless as it is, this is actually an item that could potentially be stored that we
    # return, which is why we must explicitly check for None elsewhere in the
    # framework (e.g. use has_value(...)), since "" == False but "" != None.
    if self.has_type() :
      return ""
    return None


  def _put(self, item, concrete_input_reader, current_container) :
    
    if self.has_type() :
      if not (has_value(item) and isinstance(item, str) and item == "") :
        raise LensException("Expected to PUT an empty string")
    else :  
      # Should not have been passed an item.
      if has_value(item) :
        raise LensException("Did not expect a non-store lens to be passed an item")
        
      # We could be called if there is concrete input, such that our default did not intercept.
      assert_msg(has_value(concrete_input_reader), "_put() should never be called on a non-store Empty lens without concrete input.")
      
    # Here goes nothing!
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
    concrete_reader.consume_char()
    with assert_raises(LensException) : 
      lens.get(concrete_reader)
    
    lens = Empty(mode=Empty.END_OF_TEXT)
    concrete_reader = ConcreteInputReader("h")
    # This should throw an Exception
    with assert_raises(LensException) : 
      lens.get(concrete_reader)
    concrete_reader.consume_char()
    # This should succeed quietly.
    lens.get(concrete_reader)



class Group(Lens) :
  """
  A convenience lens that thinly wraps any lens, basically to set a type.
  Usually this is used to close off a lenses container.
  """

  def __init__(self, lens, **kargs):
    super(Group, self).__init__(**kargs)
    assert_msg(self.has_type(), "To be meaningful, you must set a type on %s" % self)
    self.extend_sublenses([lens])

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
    assert(lens.put(got, "n6b3") == "a2")

    d("CREATE")
    assert(lens.put(["x", 4]) == "x4")

    d("TEST erroneous Group with no type")
    with assert_raises(AssertionError) :
      lens = Group(AnyOf(nums))


class Literal(Lens) :
  """
  A lens that deals with a constant string, usually that will not be stored.
  """

  def __init__(self, literal_string, **kargs):
    assert(isinstance(literal_string, str) and len(literal_string) > 0)
    super(Literal, self).__init__(**kargs) # Pass None for the lens, which we will build next.
    self.literal_string = literal_string
    self.default = self.literal_string
  
  def _get(self, concrete_input_reader, current_container) :
    """
    Consumes a valid char form the input, returning it if we are a STORE
    lens.
    """
    input_string = None
    try:
      input_string = concrete_input_reader.consume_string(len(self.literal_string))
      if input_string != self.literal_string :
        raise LensException("Expected the literal '%s' but got '%s'." % (escape_for_display(self.literal_string), escape_for_display(input_string)))
    except EndOfStringException:
      raise LensException("Expected literal '%s' but at end of string." % (escape_for_display(self.literal_string)))
   
    if self.has_type() :
      return input_string
    else :
      return None


  def _put(self, item, concrete_input_reader, current_container) :
    """
    If a store lens, tries to output the given char; otherwise outputs
    original char from concrete input.
    """
    # If we are not a store lens, simply return what we would consume from the input.
    if not self.has_type() :
      # We should not have been passed an item.
      assert_msg(not has_value(item), "%s did not expected to be passed an item - is a non-store lens" % self)
      if has_value(concrete_input_reader) :
        concrete_start_position = concrete_input_reader.get_pos()
        self._get(concrete_input_reader, current_container)
        return concrete_input_reader.get_consumed_string(concrete_start_position)
        
      else :
        raise NoDefaultException("Cannot CREATE: a default should have been set on lens %s, or a higher lens." % self)
    
    # If this is PUT (vs CREATE) then first consume input.
    if concrete_input_reader :
      self.get(concrete_input_reader)
    
    if item != self.literal_string :
      raise LensException("%s can not PUT." % (self, item))
    
    return item


  def _display_id(self) :
    """To aid debugging."""
    # Name is only set after Lens constructor called.
    if hasattr(self, "name") and has_value(self.name) :
      return self.name
    return "'%s'" % escape_for_display(self.literal_string)
  


  @staticmethod
  def TESTS() :
    d("GET")
    lens = Literal("xyz")
    concrete_reader = ConcreteInputReader("xyzabc")
    assert(lens.get(concrete_reader) == None and concrete_reader.get_remaining() == "abc")
    d("PUT")
    assert(lens.put(None) == "xyz")
  
    # XXX: Need to think more about this, and what it impacts.
    # Should flag that we mistakenly passed an item to a non-store low-level
    # lens that could not possibly us it.
    #with assert_raises(LensException) :
    #  lens.put("xyz")

    d("Test as STORE lens, pointless as it is with this lens.")
    lens = Literal("xyz", type=str)
    concrete_reader = ConcreteInputReader("xyzabc")
    assert(lens.get(concrete_reader) == "xyz" and concrete_reader.get_remaining() == "abc")
    concrete_reader = ConcreteInputReader("xyzabc")
    assert(lens.put("xyz", concrete_reader) == "xyz" and concrete_reader.get_remaining() == "abc")


