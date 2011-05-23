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
# Author: Nick Blundell <blundeln@gmail.com>
# Organisation: www.nickblundell.org.uk
#
"""Main API for using pylens."""


# Imports all lenses
from util_lenses import *


# Some lens abbreviations, for short-hand lens definitions.
ZM  = ZeroOrMore
OM  = OneOrMore
O   = Optional
G   = Group
WS  = Whitespace


##################################
# Main API functions
##################################

def get(lens, *args, **kargs) :
  """
  Extracts an python structure from some string structure using the given
  lens.

  Example: get(some_lens, "a=1,c=4") -> {"a":1, "c":4}
  """
  lens = BaseLens.coerce_to_lens(lens)
  return lens.get(*args, **kargs)

def put(lens_or_instance, *args, **kargs) :
  """
  Puts some python structure back into some string structure.

  Example: put(some_lens, {"a":1, "c":4}) -> "a=1,c=4"
  """
  # If we have an instance of a class which defines its own lens...
  if hasattr(lens_or_instance, "__lens__") :
    # Might as well still coerce the lens, just in case.
    lens = BaseLens.coerce_to_lens(lens_or_instance.__lens__)
    instance = lens_or_instance # For clarity.
    return lens.put(instance, *args, **kargs)
  
  # Otherwise...
  lens = BaseLens.coerce_to_lens(lens_or_instance)
  return lens.put(*args, **kargs)

def main_api_test() :
  #TODO: I'll test this with class item, since then it makes more sense.
  pass

###########################
# Main.
#

def main() :
  # This can be useful for quick testing.
  d("Testing")

if __name__ == "__main__":
  main()
