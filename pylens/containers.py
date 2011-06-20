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
import re

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

  def __new__(cls, *args, **kargs) :
    self = super(AbstractContainer, cls).__new__(cls, *args, **kargs)
    # Initialise some vars regardless of __init__ being called.
    # XXX: Perhaps mark these variables as private (i.e. prefix underscore)
    self.container_lens = None
    self.label = None
    self.alignment_mode = None
    return self

  def set_container_lens(self, lens) :
    # Called when put() is preparing the container for PUTting to associate it with its container lens.
    self.container_lens = lens
    # Default to MODEL alignment
    self.alignment_mode = self.container_lens.options.alignment or MODEL

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
    assert_msg(has_value(self.container_lens), "Our container has not been associated with a container type lens.")
   
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
    """
    A container-specific sanity check to see if this container has been fully
    consumed (i.e. all items have been PUT).

    Note, since the label item may not always be consumed (only if an is_label
    lens is used), this should be discounted.
    """
    raise NotImplementedError()
    


class ListContainer(AbstractContainer) :
  """Most basic container, for storing items in a list."""

  def __new__(cls, *args, **kargs) :
    self = super(ListContainer, cls).__new__(cls, *args, **kargs)
    self.container_item = []
    return self
  
  def __init__(self, container_item) :
    assert isinstance(container_item, list)
    self.container_item = container_item
  
    assert_msg(isinstance(self.container_item, list))

    # Ensure our items can carry meta data (for algorithmic convenience) and be careful
    # to preserve the incoming lists meta data by modifying it in place.
    # Perhaps this can be done in AbstractContainer
    for index, item in enumerate(self.container_item) :
      self.container_item[index] = enable_meta_data(item)
    
      
  def get_put_candidates(self, lens, concrete_input_reader) :
    return self.container_item
  
  def remove_item(self, item) :
    self.container_item.remove(item)

  def store_item(self, item, lens, concrete_input_reader) :
    self.container_item.append(item)

  
  def unwrap(self):
    return self.container_item

  def _get_state(self, copy_state=True) :
    state = [copy_state and copy.copy(self.container_item) or self.container_item, self.label]
    return state

  def _set_state(self, state, copy_state=True) :
    self.container_item = copy_state and copy.copy(state[0]) or state[0]
    self.label = state[1]

  def __str__(self) :
    return str(self.container_item)
  __repr__ = __str__
  
  def is_fully_consumed(self) :
    return len(self.container_item) == 0


class DictContainer(ListContainer) :
  """Allows a list of items with labels to be accessed as a native python dict."""
  
  def __init__(self, container_item) :
    """
    We actually use all the functionality of the ListContainer, which we
    can later unwrap to a dict, since items may carry labels in their
    meta data.
    """

    # Create new dict if not passed one to wrap.
    assert isinstance(container_item, dict)
    self.container_item = container_item

    # Create a list to hold the items.
    items_as_list = []

    # Now add the items to the list, updating their labels from keys.
    assert isinstance(container_item, dict)
    for key, item in container_item.iteritems() :
      item = enable_meta_data(item)
      item._meta_data.label = key
      items_as_list.append(item)

    super(DictContainer, self).__init__(items_as_list)

  # TODO: Choose default alignment mode in set_container_lens().

  def store_item(self, item, *args, **kargs) :
    if not has_value(item._meta_data.label) :
      raise LensException("%s expected item %s to have a label." % (self, item))
    super(DictContainer, self).store_item(item, *args, **kargs)

  def unwrap(self):
    # First unwrap to a list.
    items_as_list = super(DictContainer, self).unwrap()

    # Then convert to a dictionary, using item labels as keys.
    items_as_dict = {}
    for item in items_as_list :
      items_as_dict[item._meta_data.label] = item
    return items_as_dict


class LensObject(AbstractContainer) :
  """
  A container that stores labelled items as object attributes, providing
  simple converstion of lables to and from python identifiers to store as
  attributes.  For example an item with the label "Last Name" would be stored
  as an object attribute as "last_name".

  We can either constrain the attributes used with lenses or leave it open.
  
  TODO:
  - allow explicit constraining of attributes
  - think about ordering for CREATED items - praps relate to above point on
    constraining attributes.
    - perhaps proper LABEL ordering is what we want for this case - otherwise we may over complicate things
  """

  # Used to help with re-generating labels from object attribute names.  The
  # class seems a good a place as any to store this globally-useful data.
  __cached_labels = {}

  
  def __new__(cls, *args, **kargs) :
    """
    It is important that container objects can be created without arguments
    (a la serialisation), so here we initialise important variables before the
    __init__ is called.
    """
    self = super(LensObject, cls).__new__(cls, *args, **kargs)
    
    # Check for constrained attributes, define on the class.
    constrained_attributes = self._get_constrained_attributes()
    d(constrained_attributes)

    # This automatically builds a list of attributes to exclude from our
    # container's state.
    self._exclude_attributes()
    return self

  def _get_constrained_attributes(self) :
    attributes = []
    for key, value in self.__class__.__dict__.iteritems() :
      d(key)
    return attributes

  def set_container_lens(self, lens) :
    super(LensObject, self).set_container_lens(lens)
    # For a general class container, SOURCE alignment will be a more common default.
    self.alignment_mode = self.container_lens.options.alignment or SOURCE
 
  def get_put_candidates(self, lens, concrete_input_reader) :
    candidates = []
   
    # Ensure all items that may be PUT may carry meta data.
    self._enable_attributes_meta()

    for attr_name in self._get_data_attributes() :
      value = self.__dict__[attr_name]
      if has_value(value) and attr_name not in self.excluded_attributes :
        candidates.append(value)
    return candidates

 
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
    setattr(self, self._convert_label_to_attribute_name(item._meta_data.label), item)

  
  def unwrap(self):
    """We are both the container and the native object."""
    return self



  def _exclude_attributes(self) :
    """
    Just excludes attributes of our object that we do not expect to be used
    as container state.
    This should be called on object initialisation, before any model attributes
    are asigned.
    """
    self.excluded_attributes = self.__dict__.keys() + ["excluded_attributes"]

  def _convert_label_to_attribute_name(self, label) :
    """
    Tries to convert a typical label to a python identifier.  You may wish to
    overload this if you require more specialised conversion.
    """
    attribute_name = label.lower()
    # XXX: We could pre-compile this regex.
    attribute_name = re.sub(r"[ ]+", "_", attribute_name)
    
    # Check we end up with a valid python keyword.
    if not re.match(r"[a-zA-Z][a-zA-Z0-9_]*$", attribute_name) :
      raise Exception("Cannot express label '%s' as a python identifer to set as an object attribute - you will have to specialise this functionality for your purposes." % label) 
   
    # Cache this conversion on the class, since it may be useful to improve
    # CREATED labels.
    self.__class__.__cached_labels[attribute_name] = label

    return attribute_name


  def _convert_attribute_name_to_label(self, attribute_name) :
    if attribute_name in self.__class__.__cached_labels :
      return self.__class__.__cached_labels[attribute_name]

    # We assume that an underscore represents a space.
    return attribute_name.replace("_", " ")
   

  def _get_data_attributes(self) :
    """Returns the names of container items that are being used to hold data items."""
    attributes = []
    for attr_name in self.__dict__.keys() :
      if attr_name not in self.excluded_attributes and not attr_name.startswith("_"):
        attributes.append(attr_name)
    
    return attributes

  def _enable_attributes_meta(self) :
    """Enables meta on attributes that may be used as container state."""
    for attr_name in self._get_data_attributes() :
      item = enable_meta_data(self.__dict__[attr_name])
      self.__dict__[attr_name] = item
      # Ensure the label of the item is updated to match the current attribute
      # name.  If our label has changed, we need to regenerate a label.
      current_label = item._meta_data.label
      if not (has_value(current_label) and self._convert_label_to_attribute_name(current_label) == attr_name) :
        item._meta_data.label = self._convert_attribute_name_to_label(attr_name)

  def _get_state(self, copy_state=True) :
    state = copy_state and copy.copy(self.__dict__) or self.__dict__
    return state

  def _set_state(self, state, copy_state=True) :
    self.__dict__ = copy_state and copy.copy(state) or state

  def is_fully_consumed(self) :
    return len(self._get_data_attributes()) == 0


class ContainerFactory:
  """
  Used to create appropriate containers for particular types of lens.  For
  example, lens.type == dict -> container_class == DictContainer.
  """

  @staticmethod
  def get_container_class(incoming_type) :
    """
    Returns the container class associated with this type, if there is one.
    """
    if incoming_type == None:
      return None

    # If type is already an AbstractContainer, return it.
    if issubclass(incoming_type, AbstractContainer) :
      return incoming_type

    # Handle associations with native python containers.
    if issubclass(incoming_type, list) :
      return ListContainer
    elif issubclass(incoming_type, dict) :
      return DictContainer
    
    return None


  @staticmethod
  def create_container(container_lens) :
    """
    Tries to create an container appropriate for this lens and returns None
    if there is no associated container class.
    """

    # See if the lens type has a container class.
    container_class = ContainerFactory.get_container_class(container_lens.type)
    
    if container_class == None:
      return None
    
    # We do not call the constructor, which may require args.
    return container_class.__new__(container_class)

  @staticmethod
  def wrap_container(incoming_object, container_lens=None) :
    """Wraps a container if possible."""
    if incoming_object == None or issubclass(type(incoming_object), AbstractContainer) :
      return incoming_object
    
    #d("Wrapping %s" % incoming_object)
    container_class = ContainerFactory.get_container_class(type(incoming_object))
    if container_class == None :
      return None
   
    # Pass the raw data item to wrap.
    container = container_class(incoming_object)
    # Set the (consumable) label of the container based on the item's current
    # label
    container.label = incoming_object._meta_data.label
    return container
   
  # TODO: Add tests

