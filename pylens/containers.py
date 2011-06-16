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
#
#
# Author: Nick Blundell <blundeln [AT] gmail [DOT] com>
# Organisation: www.nickblundell.org.uk
#
# Description:
#  Consumable containers for abstract storage of model items.
#
import inspect
import copy
from debug import *
from exceptions import *
from util import *
from item import *
from rollback import *

# Item alignment modes for containers.
SOURCE = "SOURCE"
MODEL = "MODEL"
LABEL = "LABEL"

# Just used to simplify sorting.
LARGE_INTEGER = 0xffffffff


class AbstractContainer(Rollbackable) :
  """
  Base class for all objects that store abstract items with GET and from which
  such may be retrieved for PUT.  Meta data from the lens may be used to aid
  storage and retrieval of items in the container (e.g. labels, keys, concrete
  residue).

  We must be careful to allow the state of the container to be correctly
  captured and re-instated to facilitate efficient rollback.  In the worst
  case, we can deep-copy the state, but we should avoid this by considering
  how a particular container modifies its state during GET and PUT.  For
  example, with a list we may add or remove an item but not make finer changes
  to an item; with a general class, however, this may not be the case.
  """

  def __init__(self, lens=None) :
    assert_msg(has_value(lens), "A new container must be passed the lens that creates it.")
    
    # TODO: If we do not enclose our own lens, look for keyword of the lens.
    self.lens = lens
    self.label = None
    
    # Default to MODEL alignment mode.
    self.alignment_mode = self.lens.options.alignment or MODEL

  def set_label(self, label) :
    assert_msg(isinstance(label, str), "The container label must be a string --- at least for the time being.")
    if label and self.label :
      raise Exception("Container already has a label defined: %s" % self.label)
    self.label = label

  def get_label(self) :
    return self.label


  #
  # Can overload these for more control (e.g. tentative PUT/CREATE if non-deterministic)
  # 

  def get_and_store_item(self, lens, concrete_input_reader) :
    """Called by lenses that store items from sub-lenses in the container (e.g. And)."""
    # Note, here the lens may not have a type, though may still return an item
    # that was GOT from a sub-lens
    item = lens.get(concrete_input_reader, self)
    if has_value(item) :
      # Note, we check the actual item for is_label rather than the lens that
      # returned it, since the is_label lens may actually be a sublens.
      if item._meta_data.is_label :
        self.set_label(item) # Store item as label.
      else :
        self.store_item(item, lens, concrete_input_reader)


  def consume_and_put_item(self, lens, concrete_input_reader) :
    """Called by lenses that put items from the container into sub-lenses (e.g. And)."""
    assert(lens.has_type())
   
    # Handle is_label lens
    if lens.options.is_label:
      if not self.label :
        raise NoTokenToConsumeException("There was no item as this container's label to PUT.")
      output = lens.put(self.label, concrete_input_reader, None)
      self.label = None
      return output

    # Get candidates to PUT
    candidates = self.get_put_candidates(lens, concrete_input_reader)
    
    # Filter and sort them appropriately for our context (e.g. the lens, the
    # alignment mode and the current input postion.
    candidates = self.filter_and_sort_candidate_items(candidates, lens, concrete_input_reader)

    # XXX: Perhaps we should do alignment sorting here
    for candidate in candidates :
      try :
        # XXX : Overkill to copy initial state every time within automatic_rollback.
        with automatic_rollback(concrete_input_reader) :
          output = lens.put(candidate, concrete_input_reader, None)
          self.remove_item(candidate)
          return output
      except LensException:
        pass

    # Didn't PUT any token.
    raise NoTokenToConsumeException()


  def filter_and_sort_candidate_items(self, candidate_items, lens, concrete_input_reader) :
    """
    In some cases we can whittle down the candidate list based on properties
    of the lens, the container's alignment mode, and our position in the
    concrete_input_reader.  We can then sort them, to give preference for which
    will be tried firstmost in the consume_and_put_item() function.
    """

    # Handle a static label lens, in which the candidate choice is
    # straightforward - here, for flexibility, we assume several items may share
    # a static label.
    if has_value(lens.options.label) :
      valid_candidates = [item for item in candidate_items if item._meta_data.label == lens.options.label]
      return valid_candidates

    # Handle MODEL alignment (i.e. PUT will be in order of items in the abstract
    # model).
    if self.alignment_mode == MODEL :
      # By definition, items are already in that order.
      if len(candidate_items) > 0:
        return [candidate_items[0]]
      else:
        return [] 
    
    # Handle SOURCE alignment.
    if self.alignment_mode == SOURCE :
      # Copy candidate_items.
      def get_key(item) :
        if has_value(item._meta_data.concrete_start_position) :
          return item._meta_data.concrete_start_position
        return LARGE_INTEGER # To ensure new items go on the end.
      
      # Sort the candiates by their source order - if they have meta on their
      # source position.
      sorted_candidate_items = sorted(candidate_items, key = get_key)
      return sorted_candidate_items
    # TODO: LABEL alignment mode
    
    raise Exception("Unknown alignment mode: %s" % self.alignment_mode)


  #
  # Must overload these.
  # 

  def get_put_candidates(self, lens, concrete_input_reader) :
    """Returns a list of candidate items that could be PUT into the lens."""
    raise NotImplementedError()
  
  def remove_item(self, item) :
    raise NotImplementedError()

  def store_item(self, item, lens, concrete_input_reader) :
    raise NotImplementedError()

  def unwrap(self) :
    """Unwrap to native python type where appropriate: e.g. for list and dict.""" 
    raise NotImplementedError()

  def is_fully_consumed(self) :
    # TODO: Need to think about best way to do this.
    # This may be optional, since in some cases GET/PUT will cease when no
    # state is changed, regardless of full container consumption.
    raise NotImplementedError()
    


class ListContainer(AbstractContainer) :
  """Most basic container, for storing items in a list."""

  def __init__(self, items=None, **kargs) :
    super(ListContainer, self).__init__(**kargs)

    # Create new list if not passed one to wrap.
    if not has_value(items) :
      self.items = enable_meta_data([])
    else : 
      assert isinstance(items, list)
      self.items = items
  
    assert_msg(isinstance(self.items, list))

    # Ensure our items can carry meta data (for algorithmic convenience) and be careful
    # to preserve the incoming lists meta data by modifying it in place.
    for index, item in enumerate(self.items) :
      self.items[index] = enable_meta_data(item)
    
    # Store the label (if set) of the list in our container for stateful consumption. 
    # XXX: This should probably happen in the base class, otherwise we might
    # forget.
    self.label = self.items._meta_data.label
    
      
  def get_put_candidates(self, lens, concrete_input_reader) :
    return self.items
  
  def remove_item(self, item) :
    self.items.remove(item)

  def store_item(self, item, lens, concrete_input_reader) :
    self.items.append(item)

  
  def unwrap(self):
    # Update the label of the list (e.g. if we stored and is_label item) then return it
    self.items._meta_data.label = self.label
    return self.items

  def _get_state(self, copy_state=True) :
    state = [copy_state and copy.copy(self.items) or self.items, self.label]
    return state
      

  def _set_state(self, state, copy_state=True) :
    self.items = copy_state and copy.copy(state[0]) or state[0]
    self.label = state[1]

  def __str__(self) :
    return str(self.items)
  __repr__ = __str__


class DictContainer(ListContainer) :
  """Allows a list of items with labels to be accessed as a native python dict."""
  def __init__(self, items=None, **kargs) :
  
    # Create new dict if not passed one to wrap.
    if not has_value(items) :
      self.items = enable_meta_data([])
    else : 
      assert isinstance(items, dict)
      self.items = items

    # Create a list to hold the items.
    items_as_list = enable_meta_data([])
    

    # Now add the items to the list, updating their labels from keys.
    if has_value(items) :
      assert isinstance(items, dict)
      items_as_list._meta_data = items._meta_data
      for key, item in items.iteritems() :
        item = enable_meta_data(item)
        item._meta_data.label = key
        items_as_list.append(item)

    super(DictContainer, self).__init__(items_as_list, **kargs)

    # TODO: Choose default alignment mode.

  def store_item(self, item, *args, **kargs) :
    if not has_value(item._meta_data.label) :
      raise LensException("%s expected item %s to have a label." % (self, item))
    super(DictContainer, self).store_item(item, *args, **kargs)

  def unwrap(self):
    # First unwrap to a list.
    items_as_list = super(DictContainer, self).unwrap()

    # The convert to a dictionary.
    items_as_dict = enable_meta_data({})
    items_as_dict._meta_data = items_as_list._meta_data
    for item in items_as_list :
      items_as_dict[item._meta_data.label] = item

    return items_as_dict


class LensObject(AbstractContainer) :
  """
  A container that stores labelled items as object attributes, providing
  sensible handling of label characters.
  """

  def __init__(self, **kargs) :
    super(LensObject, self).__init__(**kargs)

    # This automatically builds a list of attributes to exclude from our
    # container's state.
    self.exclude_attributes()

    # XXX: For key-value items, when changed we will usually loose meta that could
    # have been re-used, so need to think of a nice way to preserve this.
    # Default to SOURCE alignment, which will be more likely for a general object.
    self.alignment_mode = self.lens.options.alignment or SOURCE

    # XXX: Praps something like below - need to think....
    #self.label = self._meta_data.label

  def exclude_attributes(self) :
    """
    Just excludes attributes of our object that we do not expect to be used
    as container state.
    This should be called on object initialisation, before any model attributes
    are asigned.
    """
    self.excluded_attributes = self.__dict__.keys() + ["excluded_attributes", "_meta_data"]

  def convert_label_to_attribute_name(self, label) :
    # TODO: improve this.
    attribute_name = label.replace(" ", "_")
    return attribute_name

  def convert_attribute_name_to_label(self, label) :
    pass
    
 
  def get_put_candidates(self, lens, concrete_input_reader) :
    candidates = []
    # XXX: Add meta at this stage?
    for attr_name, value in self.__dict__.iteritems() :
      if has_value(value) and attr_name not in self.excluded_attributes :
        candidates.append(value)
    return candidates

  # TODO: state get and set, so don't fallback on deep copy!
 
  def remove_item(self, item) :
    for attr_name, value in self.__dict__.iteritems() :
      if value is item :
        del self.__dict__[attr_name]
        return

    raise Exception("Failed to remove item %s from %s."% (item, self))
    

  def store_item(self, item, lens, concrete_input_reader) :
    if not has_value(item._meta_data.label) :
      raise LensException("%s expected item %s to have a label." % (self, item))
    # TODO: If constrained attributes, check within set.
    setattr(self, self.convert_label_to_attribute_name(item._meta_data.label), item)

  
  def unwrap(self):
    """We are both the container and the native object."""
    return self

class ContainerFactory:
  """Creates appropriate containers for native python types."""

  @staticmethod
  def get_container_class(incoming_type) :
    if incoming_type == None:
      return None

    if issubclass(incoming_type, AbstractContainer) :
      return incoming_type

    # Also handles auto_list
    if issubclass(incoming_type, list) :
      return ListContainer
    elif issubclass(incoming_type, dict) :
      return DictContainer
    
    return None


  @staticmethod
  def create_container(container_lens) :
    
    container_class = ContainerFactory.get_container_class(container_lens.type)
    
    if container_class == None:
      return None
    return container_class(lens = container_lens)

  @staticmethod
  def wrap_container(incoming_object, container_lens=None) :
    """Wraps a container if possible."""
    if incoming_object == None or issubclass(type(incoming_object), AbstractContainer) :
      return incoming_object
    
    #d("Wrapping %s" % incoming_object)
    container_class = ContainerFactory.get_container_class(type(incoming_object))
    if container_class == None :
      return None

    return container_class(incoming_object, lens = container_lens)
   
  # TODO: Add tests

