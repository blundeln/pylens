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
