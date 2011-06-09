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
#
#
# Author: Nick Blundell <blundeln [AT] gmail [DOT] com>
# Organisation: www.nickblundell.org.uk
# 
# Description:
#   Some tests that serve as simple examples
#
from pylens import *
from pylens.debug import d # Like print(...)

def simple_list_test() :
  INPUT_STRING = "monkeys,  monsters,    rabits, frogs, badgers"
  
  # This works like a standard parser (i.e. it extracts an abstract
  # representation of the string structure.
  # Note that, when we set a type on a lens, this instructs the lens to
  # extract and put back items of that python type from and to the string
  # structure.  In this case we wish to extract the animal names as strings to
  # store in a list, whereas we wish to discard the whitespace and delimiters.
  lens = List(Word(alphas, type=str), Whitespace("") + "," + Whitespace(" "))
  got = lens.get(INPUT_STRING)
  d(got)
  assert(got == ["monkeys", "monsters", "rabits", "frogs", "badgers"])

  # But the idea of a lens (a bi-directional parsing element) is that once we
  # have modified that abstract model, we can write it back, preserving
  # artifacts of the original string, or creating default artificats for new
  # data.
  del got[1] # Remove 'monsters'
  got.extend(["dinosaurs", "snails"])
  output = lens.put(got)
  d(output)

  # Notice, from my assert statement, that additional spacing was preserved in
  # the ouputted list and that the new items on the end use default spacing
  # that the Whitespace lenses were initialised with.
  assert(output == "monkeys,  rabits,    frogs, badgers, dinosaurs, snails")

def more_complex_structure_test() :
  INPUT_STRING = """
  people: [bill, ben]

  animals: [snake, tiger, monkey]
  food: [beans, eggs]
"""

  return
  # XXX: WORKING_HERE Note, this is working but is not terminating!
  thing_list = List(Word(alphas, type=str), Whitespace("") + "," + Whitespace(""), type=None)
  
  # Note, WS is simply an abbreviation of the Whitespace lens.
  # XXX: Have to explicty set type on Word due to nature of its construction.
  entry = Group(WS("  ") + Word(alphas, is_label=True, type=str) + WS("") + ":" + WS("") + "[" + thing_list + "]" + NewLine(), type=list)

  # Test the parts 
  assert(entry.get("  something: [a , b,c,d]\n") == ["a","b","c","d"])
 

  # XXX: Issue for GET with NewLine -> can indefinitely match at end of text.
  # XXX: State comparison does not seem to stop this.
  blank_line = WS("") + NewLine()
  lens = OneOrMore(entry | blank_line, type=dict)
  
  # For debugging: will name lenses by their local variable names.
  auto_name_lenses(locals())

  got = lens.get(INPUT_STRING)
  return
  assert(got == {'food': ['beans', 'eggs'], 'animals': ['snake', 'tiger', 'monkey'], 'people': ['bill', 'ben']})
  output = lens.put(got)
  print(output)
