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

LARGE_INTEGER = 0xffffffff


class AbstractContainer(Rollbackable) :
  """
  Base class for all objects that store abstract items with GET and from which
  such may be retrieved for PUT.  Meta data from the lens may be used to aid
  storage and retrieval of items in the container (e.g. labels, keys, concrete
  residue).
  """

  def __init__(self, lens=None) :
    assert_msg(has_value(lens), "A new container must be passed the lens that creates it.")
    self.lens = lens
    self.label = None

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
      if lens.options.is_label :
        self.set_label(item) # Store item as label.
      else :
        # Set a static label on the item if the lens defines one.
        if has_value(lens.options.label) :
          item._meta_data.label = lens.options.label
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
  
    # Ensure our items can carry meta data (for algorithmic convenience) and be careful
    # to protect the incoming lists meta data by modifying it in place.
    for index, item in enumerate(self.items) :
      self.items[index] = enable_meta_data(item)
    
    # Store the label (if set) of the list in our container for stateful consumption. 
    self.label = self.items._meta_data.label
    
    # Set the container_alignment_mode
    # In abstract ordering mode (default), take next item.
    # In source ordering mode, order by source in meta
    self.alignment_mode = self.lens.options.alignment or MODEL
  

  def get_put_candidates(self, lens, concrete_input_reader) :

    if not self.items :
      return [] # No candidates

    candidates = []
    
    # Handle a static label
    if has_value(lens.options.label) :
      candidates = [item for item in self.items if item._meta_data.label == lens.options.label]
    
    # Handle MODEL alignment
    elif self.alignment_mode == MODEL :
      if len(self.items) > 0 :
        candidates.append(self.items[0])
    
    # Handle SOURCE alignment.
    elif self.alignment_mode == SOURCE :
      def get_key(item) :
        if has_value(item._meta_data.concrete_start_position) :
          return item._meta_data.concrete_start_position
        return LARGE_INTEGER # To ensure new items go on the end.
      candidates = sorted(self.items, key = get_key)
    # TODO: LABEL mode
    else :
      raise Exception("Unknown alignment mode: %s" % self.alignment_mode)
    return candidates
  
  def remove_item(self, item) :
    self.items.remove(item)

  def store_item(self, item, lens, concrete_input_reader) :
    self.items.append(item)

  
  def unwrap(self):
    # Update the label of the list (e.g. if we stored and is_label item) then return it
    self.items._meta_data.label = self.label
    return self.items

  def __str__(self) :
    return str(self.items)


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

