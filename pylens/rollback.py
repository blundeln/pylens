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
#   Defines a Rollbackable class and util functions.
#

import copy
from debug import *
from exceptions import *


class Rollbackable(object) :
  """
  A class that can have its state rolled back, to undo modifications.
  A blanket deepcopy is not ideal, though we can explore more efficient
  solutions later (e.g. copy-before-modify).
  """

  # XXX: Do we always need to copy on get AND set? Have to careful that original state is not set.
  # XXX: Basically need to make sure that original state cannot be modified
  # XXX: Perhaps add copy-flag
  def _get_state(self, copy_state=True) :
    """
    Gets the state of this object that is required for rollback.  This is a
    catch-all function for classes that specialise Rollbackable, though where
    possible more efficient functions should be implemented.

    Usually we will wish to obtain a copy, so the original state is not
    modified, though sometimes (e.g. when comparing states) we will not require
    a copy.
    """
    if copy_state :
      return copy.deepcopy(self.__dict__)
    else :
      return self.__dict__
      

  def _set_state(self, state, copy_state=True) :
    """
    Sets the state of this object for rollback.  This is a
    catch-all function for classes that specialise Rollbackable, though where
    possible more efficient functions should be implemented.

    Usually we will wish to set a copy, so the original state is not
    modified, though sometimes we will not require
    a copy (e.g. if we know the original state will no longer be required).
    """
    if copy_state :
      self.__dict__ = copy.deepcopy(state)
    else :
      self.__dict__ = state


  def __eq__(self, other):
    """So we can easily compare if two objects have state of equal value."""
    # TODO: To use this is expensive and should be replaced by a more
    # efficient method
    # TODO:   perhaps a dirty-flag scheme???
    return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

  @staticmethod
  def TESTS():

    class SomeClass(Rollbackable):
      def __init__(self, x, y) :
        self.x, self.y = x, y

    o = SomeClass(1, [3,4])
    state1 = o._get_state()
    o.x = 3
    o.y.append(16)
    assert(o.x == 3)
    assert(o.y == [3,4,16])

    o._set_state(state1)
    assert(o.x == 1)
    assert(o.y == [3,4])

    # Test value comparision.
    o1 = SomeClass(1, [3,4])
    o2 = SomeClass(1, [3,4])
    assert(o1 == o2)
    o2.y[1] = 9
    assert(o1 != o2)
    o2.y[1] = 4
    assert(o1 == o2)



#
# Utility functions for getting and setting the state of multiple rollbackables.
#

def get_rollbackables_state(*rollbackables, **kargs) :
  """Handy function to get the state of multiple rollbackables, conviently ignoring those with value None."""
  # Assume we copy state, unless directed otherwise.
  if "copy_state" in kargs and kargs["copy_state"] == False:
    copy_state = False
  else :
    copy_state = True

  # Note: rollbackables must be in same order for get and set.
  rollbackables_state = []
  for rollbackable in rollbackables :
    if isinstance(rollbackable, Rollbackable) :
      rollbackables_state.append(rollbackable._get_state(copy_state=copy_state))
  
  #if IN_DEBUG_MODE :
  #  d("Getting state : %s" % rollbackables_state)
  
  return rollbackables_state

def set_rollbackables_state(new_rollbackables_state, *rollbackables, **kargs) :
  """Handy function to set the state of multiple rollbackables, conviently ignoring those with value None."""
  # Assume we copy state, unless directed otherwise.
  if "copy_state" in kargs and kargs["copy_state"] == False:
    copy_state = False
  else :
    copy_state = True

  #if IN_DEBUG_MODE :
  #  d("Setting state to: %s" % new_rollbackables_state)

  state_index = 0
  for rollbackable in rollbackables:
    if isinstance(rollbackable, Rollbackable) :
      rollbackable._set_state(new_rollbackables_state[state_index], copy_state=copy_state)
      state_index += 1


class automatic_rollback:
  """
  Allows rollback of reader state using the 'with' statement, for cleaner
  syntax.

  Possible extensions:
  """
  
  def __init__(self, *rollbackables, **kargs) :
    # Store the rollbackables. Note, for convenience, allow rollbackables to be None (i.e. store only Reader instances)
    self.some_state_changed = False
    self.check_for_state_change = "check_for_state_change" in kargs and kargs["check_for_state_change"] or None
    # Allows initial state to be reused.
    self.initial_state = "initial_state" in kargs and kargs["initial_state"] or None
    self.rollbackables = rollbackables
  
  def __enter__(self) :
    # Store the start state of each reader, unless we have been passed some
    # initial state to reuse.
    if self.initial_state :
      self.start_state = self.initial_state
    else :
      self.start_state = get_rollbackables_state(*self.rollbackables)
  
  def __exit__(self, type, value, traceback) :
    # If a RollbackException is thrown, revert all of the rollbackables.
    if type and issubclass(type, RollbackException) :
      set_rollbackables_state(self.start_state, *self.rollbackables)
      d("Rolled back rollbackables to: %s." % str(self.rollbackables))
   
    # XXX: Optimise this to first check for concrete reader.
    if self.check_for_state_change :
      # Not changing this state, so no need to copy it.
      current_state = get_rollbackables_state(*self.rollbackables, copy_state=False)
      #d("State: start: %s current: %s" % (self.start_state, current_state))
      self.some_state_changed = current_state != self.start_state

    # Note, by not returning True, we do not supress the exception, which gives
    # us maximum flexibility.


  @staticmethod
  def TESTS() :
    class SomeClass(Rollbackable):
      def __init__(self, x, y) :
        self.x, self.y = x, y

    o_1 = SomeClass(1, [3,4])
    o_2 = None                # Important that we can handle None to simplify code.
    o_3 = SomeClass(1, [3,4])
   
    try :
      with automatic_rollback(o_1, o_2, o_3):
        o_1.x = 3
        o_3.y.append(16)
        assert(o_1.x == 3)
        assert(o_3.y == [3,4,16])
        raise LensException() # In practice we will usually use LensException
    except LensException:
      pass # Don't wish to stop test run.
       
    # Check we rolled back.
    assert(o_1.x == 1)
    assert(o_3.y == [3,4])


