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
# Author: Nick Blundell <blundeln [AT] gmail [DOT] com>
# Organisation: www.nickblundell.org.uk
# 
# Description:
#   Utilities of global use.
#
from nbdebug import d, breakpoint, set_indent_function, IN_DEBUG_MODE

def escape_for_display(s) :
  if not IN_DEBUG_MODE :
    return s
  if len(s) == 0 :
    return "[EMPTY]"
  return s.replace("\n","[NL]").replace("\t","[TAB]") #.replace(" ","[SP]") # Escape newlines so not to confuse debug output.

def truncate(s, max_len=10) :
  """Truncates a long string so is suitable for display."""
  if not IN_DEBUG_MODE :
    return s
  MAX_LEN = max_len
  display_string = escape_for_display(s)
  if len(s) == 0 :
    return display_string # Display empty string token.
  if len(s) > MAX_LEN :
    display_string = display_string[0:MAX_LEN] + "..."
  return display_string

def range_truncate(s, max_len=10) :
  if not IN_DEBUG_MODE :
    return s
  if len(s) > max_len :
    return s[0:3] + "..." + s[-3:]
  

def assert_match(input_string, template) :
  """Flexible check to see if a string matches a template containing ellipses, for debugging."""
  # TODO: Might be an idea just to strip out whitespace completely and compare char string - or even to use a hash.
  import re
  import doctest

  # Replace \s*\n+\s* with '...', which means we can put our templates on multiple lines and indent them.
  subst_regex=re.compile(r"\s*\n+\s*")
  template = subst_regex.sub("...", template)

  # Hmmm, does this disgregard python comments?
  match = doctest._ellipsis_match(template, input_string)
  assert match, "Did not expect '%s'" % input_string



# Disable expensive functions in debug mode.
if IN_DEBUG_MODE :
  from pprint import pformat # XXX: But some tests rely on this for checking output.
else :
  pformat = lambda x:""


# XXX: Not used - yet.
class Charset:
  """Used for representing allowed characters and for handling negative sets, combination and checking for overlaps."""
  def __init__(self, charset, negate=False) :
    self.charset, self.negate = set(charset), negate
  
  def combine(self, other_charset) :
    if not isinstance(other_charset, Charset) :
      other_charset = Charset(other_charset)

    # If negation is the same, union the sets.
    if self.negate == other_charset.negate :
      return Charset(self.charset.union(other_charset.charset), negate=self.negate)

    # Handle opposite signed sets, which will always yield a negative set.
    positive_charset = self.negate and other_charset or self
    negative_charset = self.negate and self or other_charset
    return Charset(negative_charset.charset - positive_charset.charset, negate = True)


  def overlap(self, other_charset) :
    """Check if Charsets may match same characters."""
    if not isinstance(other_charset, Charset) :
      other_charset = Charset(other_charset)

    # Check intersection.
    if self.negate == False and other_charset.negate == False:
      return self.charset & other_charset.charset
    
    # Two negatives will always overlap, since space is infinite.
    if self.negate and other_charset.negate :
      return True
    
    # Handle mixed sign - no overlap if positive charset is a subset of negative subset.
    positive_charset = self.negate and other_charset or self
    negative_charset = self.negate and self or other_charset
    return not positive_charset.charset.issubset(negative_charset.charset)

  def __str__(self) :
    return "%s [%s]" % (self.negate and "not in" or "in", truncate("".join(self.charset)))

  @staticmethod
  def TESTS() :
    
    a = Charset("abcd")
    n = Charset("123")
    assert(not a.overlap(n))
    assert(a.overlap(a.combine(n)))

    not_a = Charset("abcd", negate=True)
    not_n = Charset("123", negate=True)
    assert(not_a.overlap(not_n))
    assert(not not_a.overlap(a))
    assert(not a.overlap(not_a))
    assert(a.overlap(not_n))

    newline = Charset("\n")
    not_newline = Charset("\n", negate=True)
    assert(not newline.overlap(not_newline))

    temp = newline.combine(Charset("XYZ"))
    assert(temp.charset == set(("X","Y","Z","\n")))
    temp = newline.combine(Charset("XYZ", negate=True))
    assert(temp.charset == set(("X","Y","Z")) and temp.negate)


