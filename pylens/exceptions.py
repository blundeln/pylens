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
# 
#
from nbdebug import *

# Thrown when tentative object state should be rolled back.
class RollbackException(Exception): pass

# Thrown when an abstract token collection cannot find an appropriate token in the
# PUT direction.
class NoTokenToConsumeException(RollbackException): pass

class LensException(RollbackException):
  """
  Thrown when parsing or creating lenses to trigger rollback, such that parsing
  may resume at a higher level (e.g. to try another lens path), if possible.
  """

  def __init__(self, msg=None):
    self.__msg = msg
    if IN_DEBUG_MODE :
      d("Throwing: %s (from %s)" % (self.__msg, self.get_thrown_from()))

  def get_thrown_from(self) :
    
    import inspect
    from nbdebug import getCallerLocation
    
    #TODO: Could tidy this up and perhaps integrate with nbdebug.

    ignore_frames = ["lens_assert()", "LensException.get_thrown_from()", "LensException.__init__()"]
    callerFrame = inspect.currentframe()
    location = None
    while callerFrame:
      location = getCallerLocation(callerFrame)
      if location not in ignore_frames :
        break
      callerFrame = callerFrame.f_back
    
    return location

  def __str__(self):
      return "LensException: %s" % self.__msg


class InfiniteRecursionException(Exception):
  pass

class EndOfStringException(LensException):
  pass


