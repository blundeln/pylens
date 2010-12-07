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
from nbdebug import d, breakpoint, set_indent_function, IN_DEBUG_MODE

class AbstractCollection(object) :
  
  def set_label_token(self, token, overwrite=False) :
    """When getting, don't want to allow overwriting; when putting, we want to overwrite original labels with current key."""
    assert isinstance(token, str), "Label token must be a string"
    current_label_token = self.get_label_token()
    if current_label_token :
      if not overwrite :
        raise LensException("Label token already set on %s" % self)
   
    self.label_token = token
      
  def get_label_token(self) :
    try :
      return self.label_token
    except AttributeError:
      return None

  def merge(self, other) :
    """Merge another collection into this one."""
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
    """Returns the basic type, if this collection wraps a simple type (e.g. list)"""
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
    raise NotImplementedError("in class %s" % self.__class__)


class GenericCollection(AbstractCollection):
  """
  A flexible collection that embodies a collection of tokens and which may be manipulated as a simple list or dict.
  If a token with an existing label is appended, it is simply added to the labelled list.
  """

  def __init__(self, value=None) :
    self.dict = {}

    if value != None :
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
    """Adds a new token to this token."""
    if label not in self.dict :
      self.dict[label] = []
    self.dict[label].append(item)

  def __str__(self) :
    """If possible, formats this collection to look like a simple list or dict."""
    output = []

    label_token = self.get_label_token()
    label_prefix = label_token and "<%s> ->" % label_token or ""
    if label_prefix :
      output.append("<%s> ->" % label_token)

    output.append(str(self.dict))

    return "%s: %s" % (self.__class__.__name__, " ".join(output))
  __repr__ = __str__

  #
  # Operators
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
  def TESTS() :
    t = GenericCollection(["x", 2, "Z"])
    d(t)
    d(t[0:2])
    d(GenericCollection({"a":"b", "c":"d"}))
    t = GenericCollection({"a":"b", "c":GenericCollection([1, 2])})
    t.set_label_token("a_label")
    d(t)
    d(t["a"])


class ListCollection(AbstractCollection) :
  
  def __init__(self, value=None) :
    if value :
      assert isinstance(value, list)
      self.list = value
    else :
      self.list = []
  
  def get_token(self, index=0, label=None) :
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
    return [None] # Since we wish the reader to ask us for tokens with label None

  def unwrap(self) :
    return self.list

  def _assert_no_label(self, label) :
    if label :
      raise Exception("This collection type cannot handle labelled tokens")

  def __str__(self) :
    return "%s: %s" % (self.__class__.__name__, str(self.list))
  __repr__ = __str__


class DictCollection(AbstractCollection) :
  
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

  """TODO: Could do some clever label mapping (e.g. spaces to underscores)."""

  def __init__(self, obj) :
    super(ObjectAttributeCollection, self).__init__(obj.__dict__)
    self.obj = obj
  
  def unwrap(self) :
    return self.obj
  
# Use this for user convenience, when we like to manipulate single item lists as single items.
class auto_list(list) : pass

class TokenTypeFactory:
  """Centralises all type manipulation of tokens."""

  BASIC_COLLECTION_TYPES = (list, dict, auto_list)
  BASIC_TOKEN_TYPES = (float, int)

  @staticmethod
  def get_collection_class(type) :
    """Returns the AbstractCollection class appropriate for this type."""
    if type == None :
      return GenericCollection
    
    try :
      if issubclass(type, AbstractCollection) :
        return type
    except TypeError : # Gets thrown if type not a class
      pass
    
    if issubclass(type, list) : # Also handles auto_list
      return ListCollection
    if type == dict :
      return DictCollection
    
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
    # Already normalised, so pass through.
    if isinstance(token, AbstractCollection) :
      return token

    # Handle collections.
    if isinstance(token, list) :
      return ListCollection(token)
    if isinstance(token, dict) :
      return DictCollection(token)

    # If its a simple single item, cast it to a string
    if isinstance(token, str) :
      pass # Do not modify it
    elif isinstance(token, TokenTypeFactory.BASIC_TOKEN_TYPES) :
      token = str(token)
    else :
      # Assume the token is an arbitrary object (i.e. it has attributes that can hold values).
      # XXX: Is this too flexible - should be have a base class? Depends how easily we'd like to integrate existing classes
      token = ObjectAttributeCollection(token)
    
    # Handle auto list.
    if lens_type == auto_list :
      token = ListCollection([token])

    return token

    # XXX: Hmmm,. can we always convert? I think depends on flexibilty of arbitrary object handling
    raise Exception("Do not know how to normalise %s to a string or AbstractCollection" % token)


  @staticmethod
  def cast_outgoing_token(token, target_type) :
    # Scenarios
    # - Have a simple type (str, int) want to cast from internal string token to type
    # - Have a collection type, want to cast from AbstractCollection to simple collection (e.g. list, dict)
    # - If type is auto_list and only a single item in list, return that item, rather than list.

    # Simple case: do nothing.
    if target_type == None or isinstance(token, target_type):
      return token
    
    d("Casting %s to %s" % (token, target_type))
   
    if target_type in TokenTypeFactory.BASIC_TOKEN_TYPES :
      return target_type(token) # Cast

    if (target_type in TokenTypeFactory.BASIC_COLLECTION_TYPES or inspect.isclass(target_type)) and isinstance(token, AbstractCollection) :
      type_collection_class = TokenTypeFactory.get_collection_class(target_type)
      
      if type_collection_class == token.__class__ :
        token = token.unwrap()
      else : 
        # Effectively casts one AbstractCollection to another - will fail if merge not possible
        # TODO: Need to think about how to create objs without __init__ (e.g. default args).
        new_token = type_collection_class(target_type())
        new_token.merge(token)
        token = new_token.unwrap()

      # Handle auto_list
      if target_type == auto_list :
        assert(type(token) == list)
        if len(token) == 1 :
          token = token[0]
        # XXX: Should we do anything with empty list: return None?

      return token

    raise Exception("Do not know how to cast %s to %s" % (token, target_type))
     

  @staticmethod
  def TESTS() :
    assert TokenTypeFactory.get_collection_class(list) == ListCollection
    assert TokenTypeFactory.get_collection_class(None) == GenericCollection
    
    assert TokenTypeFactory.cast_outgoing_token("123", int) == 123
    
    token = ListCollection([1,2,3])
    token = TokenTypeFactory.cast_outgoing_token(token, list)
    d(token)
    assert isinstance(token, list)

    assert TokenTypeFactory.normalise_incoming_token(3) == "3"
    assert isinstance(TokenTypeFactory.normalise_incoming_token([1, 2, 3]), ListCollection)
    assert isinstance(TokenTypeFactory.normalise_incoming_token(ListCollection([2,3])), ListCollection)



