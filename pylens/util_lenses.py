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
from core_lenses import *


class OneOrMore(Repeat) :
  def __init__(self, *args, **kargs):
    if "min_count" not in kargs :
      kargs["min_count"] = 1
    # Mental note: Don't accidentally write something like super(Repeat...
    super(OneOrMore, self).__init__(*args, **kargs)

  @staticmethod
  def TESTS() :
    # This is really just to check the lens construction.
    lens = OneOrMore(AnyOf(nums, type=int), type=list)
    assert(lens.get("123") == [1,2,3])



class ZeroOrMore(Repeat) :
  def __init__(self, *args, **kargs):
    if "min_count" not in kargs :
      kargs["min_count"] = 0
    super(ZeroOrMore, self).__init__(*args, **kargs)


class Optional(Or) :
  def __init__(self, lens, **kargs):
    super(Optional, self).__init__(lens, Empty(), **kargs)

  @staticmethod
  def TESTS():
    lens = Optional(AnyOf(alphas, type=str))
    assert(lens.get("abc") == "a")
    assert(lens.get("123") == None)
    assert(lens.put("a") == "a")
    assert(lens.put(1) == "")


class List(And) :
  """Shortcut for defining a lens-delimetered list."""
  def __init__(self, lens, delimiter_lens, **kargs):
    if "type" not in kargs :
      kargs["type"] = list
    super(List, self).__init__(lens, ZeroOrMore(delimiter_lens + lens), **kargs)

  @staticmethod
  def TESTS() :
    
    lens = List(AnyOf(nums, type=int), ",")
    d("GET")
    assert(lens.get("1,2,3") == [1,2,3])
    d("PUT")
    assert(lens.put([6,2,6,7,4,8]) == "6,2,6,7,4,8")


class NewLine(Or) :
  """Matches a newline char or the end of text, so extends the Or lens."""
  def __init__(self, **kargs) :
    super(NewLine, self).__init__("\n", Empty(mode=Empty.END_OF_TEXT), **kargs)

  @staticmethod
  def TESTS() :
    lens = NewLine()
    assert(lens.get("\n") == None)
    assert(lens.get("") == None)
    with assert_raises(LensException) :
      lens.get("abc")
    assert(lens.put("\n") == "\n")


class Word(And) :
  """
  Useful for handling keywords of a specific char range.
  """
  def __init__(self, body_chars, init_chars=None, min_count=1, max_count=None, negate=False, **kargs):

    assert_msg(min_count > 0, "min_count should be more than zero.")

    if "type" in kargs and has_value(kargs["type"]):
      assert_msg(kargs["type"] == str, "If set the type of Word should be str.")
      any_of_type = str
      # Ensure the And type is list
      kargs["type"] = list
    else :
      any_of_type = None
      and_type = None

    # Ensure chars are combined if this is a STORE lens.
    kargs["combine_chars"] = True

    left_lens = AnyOf(init_chars or body_chars, type=any_of_type)
    right_lens = Repeat(AnyOf(body_chars, type=any_of_type), min_count=min_count-1, max_count=max_count and max_count-1 or None)
    
    super(Word, self).__init__(left_lens, right_lens, **kargs)

  @staticmethod
  def TESTS() :

    lens = Word(alphanums, init_chars=alphas, type=str, max_count=5)
    d("GET")
    assert(lens.get("w23dffdf3") == "w23df")
    with assert_raises(LensException) :
      assert(lens.get("1w23dffdf3") == "w23df")

    d("PUT")
    assert(lens.put("R2D2") == "R2D2")
    
    with assert_raises(LensException) :
      lens.put("2234") == "R2D2"
    
    # XXX: Should fail if length checking working correctly.
    #with assert_raises(LensException) :
    #  lens.put("TooL0ng")
 
    
    d("Test with no type")
    lens = Word(alphanums, init_chars=alphas, max_count=5, default="a123d")
    assert(lens.get("w23dffdf3") == None)
    concrete_input_reader = ConcreteInputReader("ab12_3456")
    assert(lens.put(None, concrete_input_reader) == "ab12")
    assert(concrete_input_reader.get_remaining() == "_3456")
    assert(lens.put() == "a123d")



class Whitespace(Or) :
  """
  Whitespace helper lens, that knows how to handle (logically) continued lines with '\\n'
  or that preclude an indent which are usefil for certain config files.
  """
  
  def __init__(self, default=" ", space_chars=" \t", slash_continuation=False, indent_continuation=False, **kargs):
    # Ensure default gets passed up to parent class - we use default to
    # determine if this lens is optional

    if "type" in kargs and has_value(kargs["type"]):
      # XXX: Could adapt this for storing spaces, though to be useful would need
      # to construct in such a way as to combine chars.
      assert_msg(False, "This lens cannot be used as a STORE lens")
      
    # XXX: This could be used later when we wish to make this a STORE lens.
    word_type = None

    # TODO: Could also use default to switch on, say, indent_continuation.

    # Set-up a lens the literally matches space.
    spaces = Word(space_chars, type=word_type)
    
    or_lenses = []
    
    # Optionally, augment with a slash continuation lens.
    if slash_continuation :
      or_lenses.append(Optional(spaces) + "\\\n" + Optional(spaces))


    # Optionally, augment with a indent continuation lens.
    if indent_continuation :
      or_lenses.append(Optional(spaces) + "\n" + spaces)

    # Lastly, add the straighforward spaces lens - since otherwise this would match before the others.
    or_lenses.append(spaces)

    # If the user set the default as the empty space, the Empty must also be a valid lens.
    if default == "" :
      or_lenses.append(Empty())

    # Set up kargs for Or.
    kargs["default"] = default
    super(Whitespace, self).__init__(*or_lenses, **kargs)

  @staticmethod
  def TESTS() :
    
    # Simple whitespace.
    lens = Whitespace(" ")
    concrete_input_reader = ConcreteInputReader("  \t  xyz")
    assert(lens.get(concrete_input_reader) == None and concrete_input_reader.get_remaining() == "xyz")
    assert(lens.put() == " ")
    
    # Test that the Empty lens is valid when the default space is set to empty string (i.e. not space).
    lens = Whitespace("")
    assert(lens.get("xyz") == None)
    assert(lens.put() == "")

    # With slash continuation.
    lens = Whitespace(" ", slash_continuation=True)
    concrete_input_reader = ConcreteInputReader("  \t\\\n  xyz")
    assert(lens.get(concrete_input_reader) == None and concrete_input_reader.get_remaining() == "xyz")

    # With indent continuation.
    lens = Whitespace(" ", indent_continuation=True)
    concrete_input_reader = ConcreteInputReader("  \n xyz")
    assert(lens.get(concrete_input_reader) == None and concrete_input_reader.get_remaining() == "xyz")


#################################################
# Old stuff - for refactoring.
#################################################


##################################################
# Useful lenses
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



