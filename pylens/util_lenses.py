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



#################################################
# Old stuff - for refactoring.
#################################################


##################################################
# Useful lenses
#


class NewLine(Or) :
  """Matches a newline char or the end of text, so extends the Or lens."""
  def __init__(self, **kargs) :
    super(NewLine, self).__init__(Literal("\n", **kargs), Empty(mode=Empty.END_OF_TEXT))

  @staticmethod
  def TESTSX() :
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
  def TESTSX() :
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
  def TESTSX() :
    lens = Whitespace(" ", store=True) + Word(alphanums, store=True)
    token = lens.get("  \thello")
    assert token[1] == "hello"
    
    lens = Whitespace(" ", store=True, slash_continuation=True) + Word(alphanums, store=True)
    token = lens.get("  \t\\\n  hello")
    assert token[1] == "hello"
    
    lens = Whitespace(" ", store=True, indent_continuation=True) + Word(alphanums, store=True)
    token = lens.get("   \n hello")
    assert token[1] == "hello"


class NullLens(Lens) :
  """
  When writing new lenses, particularly in a top-down fashion, this lens is
  useful for filling in lens branches that are yet to be completed.
  """
  def _get(self, concrete_input_reader) :
    raise LensException("NullLens always fails, and is useful as a filler for the incremental writing of lenses.")
  def _put(self, abstract_token, concrete_input_reader) :
    raise LensException("NullLens always fails, and is useful as a filler for the incremental writing of lenses.")



