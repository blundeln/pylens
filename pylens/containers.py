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
#  Abstract token collection classes
#
import inspect
import copy
from debug import *
from exceptions import *
from util import *
from item import *

# Item alignment modes for containers.
SOURCE = "SOURCE"
MODEL = "MODEL"
LABEL = "LABEL"

LARGE_INTEGER = 0xffffffff

class Rollbackable(object) :
  """
  A class that can have its state rolled back, to undo modifications.
  A blanket deepcopy is not ideal, though we can explore more efficient
  solutions later (e.g. copy-before-modify).
  """

  # XXX: Do we always need to copy on get AND set? Have to careful that original state is not set.
  # XXX: Basically need to make sure that original state cannot be modified
  # XXX: Perhaps add copy-flag
  def _get_state(self) :
    return copy.deepcopy(self.__dict__)

  def _set_state(self, state) :
    self.__dict__ = copy.deepcopy(state)


  def __eq__(self, other):
    """So we can easily compare if two objects have state of equal value."""
    # TODO: To use this is expensive and should be replaced by a more efficient
    # TODO:   dirty-flag scheme.
    return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

  @staticmethod
  def TESTS():

    class SomeClass(Rollbackable):
      def __init__(self, x, y) :
        self.x, self.y = x, y

    o = SomeClass(1, [3,4])
    state1 = o._get_state()
    o.x = 3
    o.y.append(16)
    assert(o.x == 3)
    assert(o.y == [3,4,16])

    o._set_state(state1)
    assert(o.x == 1)
    assert(o.y == [3,4])

    # Test value comparision.
    o1 = SomeClass(1, [3,4])
    o2 = SomeClass(1, [3,4])
    assert(o1 == o2)
    o2.y[1] = 9
    assert(o1 != o2)
    o2.y[1] = 4
    assert(o1 == o2)



#
# Utility functions for getting and setting the state of multiple rollbackables.
#

def get_rollbackables_state(*rollbackables) :
  """Handy function to get the state of multiple rollbackables, conviently ignoring those with value None."""
  # Note: rollbackables must be in same order for get and set.
  rollbackables_state = []
  for rollbackable in rollbackables :
    if isinstance(rollbackable, Rollbackable) :
      rollbackables_state.append(rollbackable._get_state())

  #d(str(rollbackables_state))
  return rollbackables_state

def set_rollbackables_state(new_rollbackables_state, *rollbackables) :
  state_index = 0
  for rollbackable in rollbackables:
    if isinstance(rollbackable, Rollbackable) :
      rollbackable._set_state(new_rollbackables_state[state_index])
      state_index += 1


# Allows rollback of reader state using the 'with' statement.
class automatic_rollback:
  
  def __init__(self, *rollbackables) :
    # Store the rollbackables. Note, for convenience, allow rollbackables to be None (i.e. store only Reader instances)
    self.rollbackables = rollbackables
  
  def __enter__(self) :
    # Store the start state of each reader.
    self.start_state = get_rollbackables_state(*self.rollbackables)
  
  def __exit__(self, type, value, traceback) :
    # If a RollbackException is thrown, revert all of the rollbackables.
    if type and issubclass(type, RollbackException) :
      set_rollbackables_state(self.start_state, *self.rollbackables)
      d("Rolled back rollbackables to: %s." % str(self.rollbackables))
    
    # Note, by not returning True, we do not supress the exception, which gives
    # us maximum flexibility.


  @staticmethod
  def TESTS() :
    
    class SomeClass(Rollbackable):
      def __init__(self, x, y) :
        self.x, self.y = x, y

    o_1 = SomeClass(1, [3,4])
    o_2 = None                # Important that we can handle None to simplify code.
    o_3 = SomeClass(1, [3,4])
   
    try :
      with automatic_rollback(o_1, o_2, o_3):
        o_1.x = 3
        o_3.y.append(16)
        assert(o_1.x == 3)
        assert(o_3.y == [3,4,16])
        raise LensException() # In practice we will usually use LensException
    except LensException:
      pass # Don't wish to stop test run.
       
    # Check we rolled back.
    assert(o_1.x == 1)
    assert(o_3.y == [3,4])


#
# Containers
#

class AbstractContainer(Rollbackable) :
  """
  Base class for all objects that store abstract items with GET and from which
  such may be retrieved for PUT.  Meta data from the lens may be used to aid
  storage and retrieval of items in the container (e.g. labels, keys, concrete
  residue).
  """

  def __init__(self, lens=None) :
    assert_msg(has_value(lens), "A new container must be passed a lens.")
    self.lens = lens

  def set_label(self, label) :
    if label and self.label :
      raise Exception("Container already has a label defined.")
    self.label = label

  def get_label(self) :
    if hasattr(self, "label") :
      return self.label
    else :
      return None


  #
  # Can overload these for more control (e.g. tentative PUT/CREATE if non-deterministic)
  # 

  def get_and_store_item(self, lens, concrete_input_reader) :
    """Called by lenses that store items from sub-lenses in the container (e.g. And)."""
    # Note, here the lens may not have a type, though may still return an item
    # that was GOT from a sub-lens
    item = lens.get(concrete_input_reader, self)
    if has_value(item) :
      self.store_item(item, lens, concrete_input_reader)
 
  def consume_and_put_item(self, lens, concrete_input_reader) :
    """Called by lenses that put items from the container into sub-lenses (e.g. And)."""
    assert(lens.has_type())
    
    # Get candidates to PUT
    candidates = self.get_put_candidates(lens, concrete_input_reader)
    for candidate in candidates :
      try :
        # TODO : Overkill to copy initial state every time within automatic_rollback.
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




class ListContainer(AbstractContainer) :
  """Simply stores items in a list, making no use of meta data."""

  def __init__(self, initial_list=None, **kargs) :
    super(ListContainer, self).__init__(**kargs)
    
    # Use list if passed; otherwise create a new list.
    if initial_list != None :
      assert isinstance(initial_list, list)
      # Ensure items can hold meta data
      self.list = [attach_meta_data(item) for item in initial_list]
    else :
      self.list = []

  def get_put_candidates(self, lens, concrete_input_reader) :

    if not self.list :
      return [] # No candidates

    # In abstract ordering mode (default), take next item.
    # In source ordering mode, order by source in meta
    container_alignment_mode = self.lens.options.alignment or MODEL

    candidates = []
    if container_alignment_mode == MODEL :
      if len(self.list) > 0 :
        # TODO: Check type compatible with lens.
        candidates.append(self.list[0])
    elif container_alignment_mode == SOURCE :
      def get_key(item) :
        if has_value(item._meta_data.start_position) :
          return item._meta_data.start_position
        return LARGE_INTEGER # To ensure new items go on the end.
      candidates = sorted(self.list, key = get_key)
    # TODO: LABEL mode
    else :

      raise Exception("Unknown alignment mode: %s" % container_alignment_mode)
    return candidates
  
  def remove_item(self, item) :
    self.list.remove(item)

  def store_item(self, item, lens, concrete_input_reader) :
    self.list.append(item)

  
  def unwrap(self):
    return self.list

  def __str__(self) :
    return str(self.list)

  @staticmethod
  def TESTS() :
    # Dummy arguments
    lens, concrete_input_reader = None, None

    # TODO: Redo these
    return


# XXX: Deprecate
class UnorderedListContainer(ListContainer) :
  """
  Container that tries to respect original positioning of items in the concrete
  input, where possible.  It is tempting to use a python set, though this
  requires items to be immutable (for hashability). 
  """

  def __init__(self, initial_list=None) :
    # Use list if passed; otherwise create a new list.
    if initial_list != None :
      if not isinstance(initial_list, unordered_list) :
        assert isinstance(initial_list, list)
        self.list = unordered_list(initial_list)
      self.list = initial_list
    else :
      self.list = unordered_list()
    
  def get_put_candidates(self, lens, concrete_input_reader) :
    candidates = []

    # Want to end up with items in postional order or fall back on abstract order.
    
    # Note: if item is auto_list item need to get correct position from it.

    # Start with candidate list
    candidates = self.list[:]


    return candidates


  def consume_item(self, lens, concrete_input_reader) :
    # XXX: What if someone copies an item such that multiple have same source in meta?
    # XXX: Need to handle auto list here, surely.

    # First try to put an item back into this position
    # Failing that, put any suitable item.

    #
    # Sort the items into positional and non-positional.
    #
    # XXX: Not good to build this every time, but okay for now.
    items_with_meta = {}
    items_without_meta = []
    for item in self.list :
      if item_has_meta(item) :
        assert(has_value(item._meta_data.start_position))
        # TODO: handle auto_list position that may be embedded in item.
        items_with_meta[item._meta_data.start_position] = item
      else :
        items_without_meta.append(item)

    if concrete_input_reader :
      current_input_position = concrete_input_reader.get_pos()
    else :
      current_input_position = None

    # See if we have an item that aligns with out current position.
    if has_value(current_input_position) and current_input_position in items_with_meta:
      item = items_with_meta[current_input_position]
      self.list.remove(item)
      return item

    # If we haven't yet returned an item that matches positionally, return any non-positional item (e.g. a new item).
    try :
      item = items_without_meta.pop(0)
      self.list.remove(item)
      return item
    except IndexError:
      raise NoTokenToConsumeException()
  
  
  @staticmethod
  def TESTS() :

    from pylens import Repeat, Group, AnyOf, alphas, nums

    # TODO
    return

    lens = Repeat(Group(AnyOf(alphas, type=str) + AnyOf("*+-", default="*") + AnyOf(nums, type=int), type=list), type=unordered_list)
    # XXX lens = Repeat(Group(AnyOf(alphas, type=str) + AnyOf("*+-", default="*") + AnyOf(nums, type=int), type=list), type=list, alignment=model)

    d("GET")
    got = lens.get("a+3c-2z*7")
    assert(got == [["a",3],["c",2],["z",7]])

    # Move the front item to the end - should not affect positional ordering.
    got.append(got.pop(0))

    output = lens.put(got)
    d(output)
    assert(output == "a+3c-2z*7")



class DictContainer(AbstractContainer) :
  """Stores items in a dict."""

  def __init__(self, dictionary=None) :
    # Use list if passed; otherwise create a new list.
    if has_value(dictionary) :
      assert isinstance(dictionary, dict)
      self.dictionary = dictionary
    else :
      self.dictionary = {}


  def store_item(self, item, lens, concrete_input_reader) :
    
    key = None
    
    if lens.options.label :
      if lens.options.label in self.dictionary :
        raise CannotStoreException("Label '%s' is already in use" % lens.options.label)
      key = lens.options.label

    if key :
      self.dictionary[key] = item
      return

    raise CannotStoreException("I do not know how to store this lens item.")


  def consume_item(self, lens, concrete_input_reader) :
    
    key = None

    if lens.options.label and lens.options.label in self.dictionary:
      key = lens.options.label

    if key :
      item = self._get_and_remove(key)
      return item

    raise NoTokenToConsumeException("I cannot find an item in the dictionary approriate for the lens.")
    

  def _get_and_remove(self, key) :
    item = self.dictionary[key]
    del self.dictionary[key]
    return item

  def unwrap(self):
    return self.dictionary

  def __str__(self) :
    return str(self.dictionary)

  @staticmethod
  def TESTS() :

    from pylens.base_lenses import Group, AnyOf, alphas, nums

    # TODO: Update these
    return

    #
    # Test use of static labels.
    #

    lens = Group(AnyOf(nums, type=int, label="number") + AnyOf(alphas, type=str, label="character"), type=dict)
    assert(lens.get("1a") == {"number":1, "character":"a"})
    assert(lens.put({"number":4, "character":"q"}, "1a") == "4q")
    #assert(lens.create({"number":4, "character":"q"}) == "4q")
    with assert_raises(NoTokenToConsumeException) :
      lens.put({"number":4, "wrong_label":"q"}, "1a")
    
    #
    # Test use of dynamic labels.
    #

    # TODO:



class ContainerFactory:
  """Creates appropriate containers for native python types."""
 

  @staticmethod
  def get_container_class(incoming_type) :
    if incoming_type == None:
      return None

    if issubclass(incoming_type, AbstractContainer) :
      return incoming_type

    # Also handles auto_list
    if issubclass(incoming_type, unordered_list) :
      raise Exception("Deprecated") #XXX
      return UnorderedListContainer
    elif issubclass(incoming_type, list) :
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
    





















# OLD STUFF ===================================================

class AbstractCollection(object) :
  """
  Base class/interface for all token collections.

  A collection can hold a set of tokens, in some collection dependent order,
  and a key token.
  """

  def set_label_token(self, token, allow_overwrite=False) :
    """
    When getting, don't want to allow overwriting; when putting, we want to
    overwrite original labels with current key.
    """
    assert isinstance(token, str), "Label token must be a string"
    current_label_token = self.get_label_token()
    if current_label_token :
      if not allow_overwrite :
        # XXX: Should this be a show stopper?
        raise Exception("Label token already set on %s so cannot be set to '%s'" % (self, token))
        #raise LensException("Label token already set on %s" % self)
   
    self.label_token = token
      
  def get_label_token(self) :
    try :
      return self.label_token
    except AttributeError:
      return None

  def merge(self, other) :
    """
    Merges another collection into this one, which is important for the
    effective casting of collection types.
    """
    # Ensure we get the same class, though perhaps we can relax this.
    assert isinstance(other, AbstractCollection)
    d("Merging %s into %s" % (other, self))

    # Handle the label token, which will travel downstream.
    other_label_token = other.get_label_token()
    if other_label_token :
      self.set_label_token(other_label_token)

    # Now merge the tokens.
    for label in other.get_labels():
      for index in range(other.get_no_tokens(label)):
        self.add_token(other.get_token(index, label=label), label=label)

  def unwrap(self) :
    """
    Returns the basic type for ease of user manipulation, if this collection
    wraps a simple type (e.g. list), otherwise return the collection.
    """
    return self
  
  #
  # For overloading
  #
  
  def get_token(self, index=0, label=None) :
    """Should return None if the token cannot be found."""
    raise NotImplementedError("in class %s" % self.__class__)

  def get_labels(self) :
    raise NotImplementedError("in class %s" % self.__class__)
  
  def add_token(self, token, label=None) :
    raise NotImplementedError("in class %s" % self.__class__)

  def get_no_tokens(self, label=None) :
    """Gets the number of tokens stored under a particular label."""
    raise NotImplementedError("in class %s" % self.__class__)


class GenericCollection(AbstractCollection):
  """
  A flexible collection that embodies a collection of tokens and which may be
  manipulated as a simple list or dict.  If a token with an existing label is
  appended, it is simply added to the labelled list.

  Note that is does not make sense for this collection to be unwrapped, since
  it does not represent one simple collection type.
  """

  def __init__(self, value=None) :
    # We use a dict to store everything.
    self.dict = {}

    if value == None:
      return

    if isinstance(value, list) :
      self.dict[None] = value    # None key means: no label.
    elif isinstance(value, dict) :
      for key in value :
        self.dict[key] = [value[key]] # Items should be in a list, to handle multiple tokens with same label.
    else :
      raise Exception("Expected some sort of collection: a dictionary or list")

  def get_labels(self) :
    return self.dict.keys()

  def get_no_tokens(self, label=None) :
    tokens = self.dict[label]
    assert(isinstance(tokens, list))
    return len(tokens)
  
  def get_token(self, index=0, label=None) :
    try :
      return self.dict[label][index]
    except KeyError:
      return None

  def add_token(self, item, label=None) :
    """Adds a new token under the specicifed label, appending a list if label exists already."""
    if label not in self.dict :
      self.dict[label] = []
    self.dict[label].append(item)

  def __str__(self) :

    """If possible, formats this collection to look like a simple list or dict - to aid debugging."""
    output = []

    label_token = self.get_label_token()
    label_prefix = label_token and "<%s> ->" % label_token or ""
    if label_prefix :
      output.append("<%s> ->" % label_token)

    output.append(str(self.dict))

    return "%s: %s" % (self.__class__.__name__, " ".join(output))
  __repr__ = __str__

  #
  # Override operators, for convenient attribute-like manipulation.
  #
  def __getitem__(self, key) :
    # Restrict strings for dict keys, so list handles slices (e.g. x[3:5]) etc.
    if isinstance(key, str) :
      return self.dict[key][0]
    else :
      return self.dict[None][key]
   
  def __setitem__(self, key, value) :
    if isinstance(key, str) :
      self.dict[key] = [value]
    else :
      self.dict[None][key] = value


  @staticmethod
  def xTESTS() :
    t = GenericCollection(["x", 2, "Z"])
    d(t)
    d(t[0:2])
    d(GenericCollection({"a":"b", "c":"d"}))
    t = GenericCollection({"a":"b", "c":GenericCollection([1, 2])})
    t.set_label_token("a_label")
    d(t)
    d(t["a"])
    # TODO: Should acutally test these outputs.


class ListCollection(AbstractCollection) :
  """Represents a simple list of tokens (i.e. no labels allow, other than label token).""" 
  
  def __init__(self, value=None) :
    # Use list if passed; otherwise create a new list.
    if value :
      assert isinstance(value, list)
      self.list = value
    else :
      self.list = []
  
  def get_token(self, index=0, label=None) :
    # Returns token, or None if not possible.
    if label :
      return None
    
    try :
      return self.list[index]
    except IndexError:
      return None

  def add_token(self, token, label=None) :
    self._assert_no_label(label)
    self.list.append(token)

  def get_no_tokens(self, label=None) :
    self._assert_no_label(label)
    return len(self.list)

  def get_labels(self) :
    # Return the None label, since we wish the reader to ask us for tokens with label None
    return [None]

  def unwrap(self) :
    """Returns the inner python list."""
    return self.list

  def _assert_no_label(self, label) :
    if label != None:
      raise Exception("This collection type cannot handle labelled tokens")

  def __str__(self) :
    return "%s: %s" % (self.__class__.__name__, str(self.list))
  __repr__ = __str__


class DictCollection(AbstractCollection) :
  """
  Wraps a dictionary.
  """
  def __init__(self, value=None) :
    if value != None :
      assert isinstance(value, dict)
      self.dict = value
    else :
      self.dict = {}
  
  def get_token(self, index=0, label=None) :
    assert index == 0, "Can access token only by index=0"
    try :
      return self.dict[label]
    except KeyError:
      return None

  def add_token(self, token, label=None) :
    if label in self.dict :
      raise Exception("Can store only a single token per label (%s) in this AbstractCollection" % label)
    self.dict[label] = token

  def get_no_tokens(self, label=None) :
    if label in self.dict :
      return 1
    else :
      return 0

  def get_labels(self) :
    return self.dict.keys()

  def unwrap(self) :
    return self.dict

  def __str__(self) :
    return "%s: %s" % (self.__class__.__name__, str(self.dict))
  __repr__ = __str__


class ObjectAttributeCollection(DictCollection) :
  """
  Extends the DictCollection to provide a general object wrapper, where labels
  represent object attributes.
  """
  # TODO: Could do some clever label mapping (e.g. spaces to underscores).
  # Would also be good to allow hooks if we know class type.

  def __init__(self, obj) :
    # This allows the object's attributes to be manipulated by our parent class.
    # XXX: This may well hinder flexibility, if we would like some possibility
    # of hooking attribute access (e.g. to allow some processing to occur in
    # the model class if desired).
    super(ObjectAttributeCollection, self).__init__(obj.__dict__)
    self.obj = obj
  
  def unwrap(self) :
    return self.obj
  

class TokenTypeFactory:
  """
  Centralises all type manipulation of tokens.
  """

  BASIC_COLLECTION_TYPES = (list, dict, auto_list)
  BASIC_TOKEN_TYPES = (float, int)

  @staticmethod
  def get_appropriate_collection_class(type) :
    """Returns the AbstractCollection class appropriate for this type."""

    # This is the default, most-flexible collection, to use when user does not specify type.
    if type == None :
      return GenericCollection
  
    # TODO: We could assert we have a class here.

    try :
      if issubclass(type, AbstractCollection) :
        return type
    except TypeError : # Gets thrown if type not a class
      pass
    
    if issubclass(type, list) : # Also handles auto_list
      return ListCollection
    if type == dict :
      return DictCollection
    
    # For general classes (e.g. user's data model classes)
    if inspect.isclass(type) :
      return ObjectAttributeCollection

    raise Exception("Cannot match type %s to a AbstractCollection" % type)

  @staticmethod
  def normalise_incoming_token(token, lens_type=None) :
    """
    Ensures the token is converted appropriately either to a AbstractCollection or a string.
    A special case is when we have a single item and the lens has type auto_list, which
    means we must enclose that item in a list.
    """

    # Algorithm Outline
    # - Need to ensure whatever gets passed is appropriately converted to a string or a collection type for internal lens processing.
    # - Easy case: if we get an AbstractCollection, pass straight through with no pre-processing.
    # - Next: if we have a python collection or a user model class instance, wrap in an appropriate AbstractCollection
    # - If we have a simple type, cast to string. 
    # - A special case is where the lens type is an auto_list, which requires a single token to be wrapped within a ListCollection
    #   - This single token can be a string (parhaps cast from an int, float, etc.) or an ObjectAttributeCollection.

    # Already normalised, so pass through.
    if isinstance(token, AbstractCollection) :
      return token

    # Handle collection wrapping.
    if isinstance(token, list) : # Or auto_list
      return ListCollection(token)
    if isinstance(token, dict) :
      return DictCollection(token)

    # Now we assume we have been passed a single (rather than a collection) token.

    # If a string already, pass it through.
    if isinstance(token, str) :
      pass # Do not modify it
    # Else, if a simple type, cast to string.
    elif isinstance(token, TokenTypeFactory.BASIC_TOKEN_TYPES) :
      token = str(token)
    # Assume the token is an arbitrary object that is part of the user's data
    # model (i.e. it has attributes that can hold values).
    else:
      # XXX: Is this too flexible - should be have a base class? Depends how
      # easily we'd like to integrate existing classes
      token = ObjectAttributeCollection(token)

    # Now we assume the token is a string or ObjectAttributeCollection.
    assert isinstance(token, (str, ObjectAttributeCollection))

    # Now handle the special case where the lens is defined as an auto_list,
    # which requires that single token is actually wrapped in a ListCollection.
    if lens_type == auto_list :
      token = ListCollection([token])

    return token


  @staticmethod
  def cast_outgoing_token(token, target_type) :
    """
    For use at the edge of the API to allow internal tokens to be cast to
    convenient python types, if possible, allowing the user to work with
    convenient data structures (e.g. their model classes, int, float, list,
    dict, etc.)
    """
    # Algorithm Outline
    # - Our token may be a single token to be cast to the specified simple type (e.g. str, int, float).
    # - Or, it may be collecion class, which is to be unwraped to its enclosed python collection or instance of a user's model class.
    # - In the special case, where target_type is auto_list, then a ListCollection of a single item will be unwrapped to the first item.

    # Simple case: do nothing if no specific type or token already of that type.
    if target_type == None or isinstance(token, target_type):
      return token
    
    d("Casting %s to %s" % (token, target_type))
   
    # Handle straightforward cast (e.g. int("1234"), float("123.443"))
    if target_type in TokenTypeFactory.BASIC_TOKEN_TYPES :
      return target_type(token)

    # Now we expect to be dealing with an AbstractCollection token, which could
    # end up being cast either to a simple python collection type or to an
    # instance of a class from the users abstract data model.
    assert isinstance(token, AbstractCollection), "Expected an AbstractCollection to cast to a model object or a native python collection"

    # Get the (internally-used) collection class for this type.
    target_type_collection_class = TokenTypeFactory.get_appropriate_collection_class(target_type)

    # If the target type is actually wrapped in the collection, simply unwrap it.
    if target_type_collection_class == token.__class__ :
      token = token.unwrap()
    
    # Otherwise, we must effectively cast from one collection to another
    # before unwrapping, which will fail naturally if the collections in the
    # conversion are not compatible, thanks to the well-defined
    # AbstractCollection interface.
    else : 
      # First, create a new collection appropriate for the target type,
      # wrapping an empty instance of target_type.
      # TODO: Distinguish user model classes
      # http://docs.python.org/reference/datamodel.html#newstyle
      try :
        new_instance = target_type.__new__(target_type)
      except AttributeError:
        raise Exception("Cannot create instance of %s with __new__() (i.e.  without calling init()), check the class is a new-style class (i.e. extends object)" % target_type)
      new_token = target_type_collection_class(new_instance)
      # The merge in data from the original token (collection)
      new_token.merge(token)
      # Now unwrap it to give us the desired python collection type.
      token = new_token.unwrap()

    # Handle auto_list behaviour, which further unwraps the token if a list of len 1.
    if target_type == auto_list and isinstance(token, list) and len(token) == 1 :
      token = token[0]
      # XXX: Should we do anything with empty list: return None?
      #      Would need to consider also in the PUT direction.

    return token
     

  @staticmethod
  def xTESTS() :
    assert TokenTypeFactory.get_appropriate_collection_class(list) == ListCollection
    assert TokenTypeFactory.get_appropriate_collection_class(None) == GenericCollection
    
    assert TokenTypeFactory.cast_outgoing_token("123", int) == 123
    
    token = ListCollection([1,2,3])
    token = TokenTypeFactory.cast_outgoing_token(token, list)
    d(token)
    assert isinstance(token, list)

    assert TokenTypeFactory.normalise_incoming_token(3) == "3"
    assert isinstance(TokenTypeFactory.normalise_incoming_token([1, 2, 3]), ListCollection)
    assert isinstance(TokenTypeFactory.normalise_incoming_token(ListCollection([2,3])), ListCollection)
