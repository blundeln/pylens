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
  return s.replace("\n","<NL>").replace("\t","<TAB>").replace(" ","<SP>") # Escape newlines so not to confuse debug output.

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

# Disable expensive functions in debug mode.
if IN_DEBUG_MODE :
  from pprint import pformat # XXX: But some tests rely on this for checking output.
else :
  pformat = lambda x:""
