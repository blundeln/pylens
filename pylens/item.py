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
# 
#

from debug import *
from util import *

META_ATTRIBUTE = "_meta_data"

#
# Wrappers for simple types, so we can transparently add arbitrary properies.
#
class str_wrapper(str) :pass
class int_wrapper(int) :pass
class float_wrapper(float) :pass
class list_wrapper(list) :pass
#class unordered_list_wrapper(unordered_list) :pass
class dict_wrapper(dict) :pass

#
# Custom types.
#



# Use this for user convenience, when we like to manipulate single item lists
# as single items and auto convert those single items to and from lists at the
# edge of the API.
class auto_list(list_wrapper) : pass

# Signifies that a lens will use an UnorderedListContainer.
class unordered_list(list_wrapper): pass




def item_has_meta(item) :
  return hasattr(item, META_ATTRIBUTE) 

def attach_meta_data(item) :
  """Adds a flexible Properties attribute to any object (inc. simple types) for storing meta data."""  
  assert(has_value(item))

  if not item_has_meta(item) : 
    
    # Wrap simple types to allow attributes to be added to them.
    if isinstance(item, str) : item = str_wrapper(item)
    elif isinstance(item, float) : item = float_wrapper(item)
    elif isinstance(item, int) : item = int_wrapper(item)
    elif isinstance(item, list) : item = list_wrapper(item)
    elif isinstance(item, dict) : item = dict_wrapper(item)
   
    setattr(item, META_ATTRIBUTE, Properties())
  
  return item


#
# TESTS
#

def item_meta_test() :
  d("Started")
  item = "hello"
  item = attach_meta_data(item)

  # Should be able to add any attribute.
  item._meta_data.monkeys = True
  assert(item._meta_data.monkeys == True)
  assert(item._meta_data.bananas == None)
