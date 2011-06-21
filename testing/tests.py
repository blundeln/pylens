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
#  Longer tests, which must have suffix '_test' to be picked up for automated
#  testing.  Some of these are based on tricky config file examples given in the Augeas system
#  Note that these lenses may not be completely accurate but are an aid to testing. 
# 

from pylens import *


def auto_list_test() :
  lens = Repeat(AnyOf(nums, type=int), type=list, auto_list=True)
  d("GET")
  assert(lens.get("123") == [1,2,3])
  assert(lens.get("1") == 1)
  
  d("PUT")
  assert(lens.put([5,6,7]) == "567")
  assert(lens.put(5) == "5")

  # Test list_source_meta_data preservation - assertion will fail if not preserved.
  assert(lens.put(lens.get("1")) == "1")


def dict_test() :

  
  # Test use of static labels.
  lens = Group(AnyOf(nums, type=int, label="number") + AnyOf(alphas, type=str, label="character"), type=dict, alignment=SOURCE)
  d("GET")
  assert(lens.get("1a") == {"number":1, "character":"a"})
  d("PUT")
  assert(lens.put({"number":4, "character":"q"}, "1a") == "4q")
  with assert_raises(NoTokenToConsumeException) :
    lens.put({"number":4, "wrong_label":"q"}, "1a")
  
 
  # Test dynamic labels
  key_value_lens = Group(AnyOf(alphas, type=str, is_label=True) + AnyOf("*+-", default="*") + AnyOf(nums, type=int), type=list)
  lens = Repeat(key_value_lens, type=dict, alignment=SOURCE)

  d("GET")
  got = lens.get("a+3c-2z*7")
  d(got)
  assert(got == {"a":[3], "c":[2], "z":[7]})
  
  d("PUT")
  output = lens.put({"b":[9], "x":[5]})
  d(output)
  assert(output in ["b*9x*5","x*5b*9"]) # Could be any order.

  d("Test manipulation")
  got = lens.get("a+3c-2z*7")
  del got["c"]
  output = lens.put(got)
  assert(output == "a+3z*7") # Should have kept SOURCE alignment.

  d("Test with auto list, which should keep source state")
  key_value_lens = Group(AnyOf(alphas, type=str, is_label=True) + AnyOf("*+-", default="*") + AnyOf(nums, type=int), type=list, auto_list=True)
  lens = Repeat(key_value_lens, type=dict, alignment=SOURCE)

  d("GET")
  got = lens.get("a+3c-2z*7")
  d(got)
  assert(got == {"a":3, "c":2, "z":7})
  d("PUT")
  output = lens.put(got)
  assert(output == "a+3c-2z*7")
 
  # For now this will loose some concrete, but later we will consider user-implied alignment
  # or at least label alignment rather than source alignment.
  d("Test auto_list with modification.")
  got = lens.get("a+3c-2z*7")
  got["c"] = 4
  output = lens.put(got)
  assert_equal(output, "a+3z*7c*4")



def consumption_test():
 
  test_description("Test input consumption")
  lens = Repeat(AnyOf(nums, type=int), type=list)
  with assert_raises(NotFullyConsumedException):
    lens.get("123abc") # This will leave 'abc'

  with assert_raises(NotFullyConsumedException):
    lens.put([1,2], "123abc")  # This will leave 'abc'

  test_description("Test container consumption")
  
  # This will consume input but leave "a" in list.
  with assert_raises(NotFullyConsumedException):
    lens.put([1,2,"a"], "67")


def list_test() :

  lens = Repeat(AnyOf(nums, type=int), type=list)
  d("GET")
  assert(lens.get("123") == [1,2,3])
  
  d("PUT")
  assert(lens.put([5,6,7]) == "567")

  d("GET-PUT")
  assert(lens.put(lens.get("1")) == "1")


def model_ordered_matching_list_test() :
  
  lens = Repeat(
    Group(AnyOf(alphas, type=str) + AnyOf("*+-", default="*") + AnyOf(nums, type=int), type=list),
    type=list, alignment=MODEL)

  d("GET")
  got = lens.get("a+3c-2z*7")
  assert(got == [["a",3],["c",2],["z",7]])

  # Move the front item to the end - should affect positional ordering.
  got.append(got.pop(0))

  output = lens.put(got)
  d(output)
  assert(output == "c-2z*7a+3")

  d("With deletion and creation")
  d("GET")
  got = lens.get("a+3c-2z*7")
  # Move the front item to the end - should affect positional ordering.
  got.append(got.pop(0))
  # Now remove the middle item
  del got[1] # z*7
  # And add a new item
  got.append(["m",6])

  output = lens.put(got)
  d(output)
  assert(output == "c-2a+3m*6")



def source_ordered_matching_list_test() :

  lens = Repeat(
    Group(AnyOf(alphas, type=str) + AnyOf("*+-", default="*") + AnyOf(nums, type=int), type=list),
    type=list, alignment=SOURCE)

  d("Without deletion")
  d("GET")
  got = lens.get("a+3c-2z*7")
  assert(got == [["a",3],["c",2],["z",7]])

  # Move the front item to the end - should affect positional ordering.
  got.append(got.pop(0))

  output = lens.put(got)
  d(output)
  assert_equal(output, "a+3c-2z*7")

  d("With deletion and creation")
  d("GET")
  got = lens.get("a+3c-2z*7")
  # Move the front item to the end - should affect positional ordering.
  got.append(got.pop(0))
  # Now remove the middle item
  del got[1] # z*7
  # And add a new item
  got.append(["m",6])

  output = lens.put(got)
  d(output)
  assert(output == "a+3c-2m*6")

def state_recovery_test():

  test_description("Test that the user's item's state is recovered after consumption.")
  INPUT = "x=y;p=q"
  lens = List(KeyValue(Word(alphas, is_label=True)+"="+Word(alphas, type=str)), ";", type=dict)
  got = lens.get(INPUT)
  my_dict = {}
  my_dict["beans"] = "yummy"
  my_dict["marmite"] = "eurgh"
  lens.put(my_dict)
  assert_equal(my_dict, {"beans":"yummy", "marmite":"eurgh"})
  # XXX: Actually, due to DictContainer implementation, this state would not be
  # lost anyway, though a similar test with LensObject below flexes this test
  # case.  I will leave this test, should the implemenation change in someway to
  # warrent this test case.


def lens_object_test():
  """
  Here we demonstrate the use of classes to define our data model which are
  related to a lens.
  """

  # Define our Person class, which internally defines its lens.
  class Person(LensObject) :
    __lens__ = "Person::" + List(
      KeyValue(Word(alphas+" ", is_label=True) + ":" + Word(alphas+" ", type=str)),
      ";",
      type=None # XXX: I should get rid of default list type on List
    )
    
    def __init__(self, name, last_name) :
      self.name, self.last_name = name, last_name

  test_description("GET")
  # Here we use the high-level API get() function, which is for convenience and
  # which equates to:
  #  lens = Group(Person.__lens__, type=Person)
  #  person = lens.get("Person::Name:nick;Last   Name:blundell")
  person = get(Person, "Person::Name:nick;Last   Name:blundell")
  assert(person.name == "nick" and person.last_name == "blundell")
  test_description("PUT")
  
  # Now we PUT it back with no modification and should get what we started with.
  output = put(person)
  assert_equal(output, "Person::Name:nick;Last   Name:blundell")
  # And we do this again to check the consumed state of person was restored
  # after the successful PUT.
  output = put(person)
  assert_equal(output, "Person::Name:nick;Last   Name:blundell")

  test_description("CREATE")
  new_person = Person("james", "bond")
  output = put(new_person)
  
  # Test that consumed state is restored on a successful PUT.
  assert(new_person.name == "james" and new_person.last_name == "bond")
  
  # XXX: Would be nice to control the order, but need to think of a nice way to
  # do this - need to cache source info of a label, which we can use when we
  # loose source info, also when a user declares attributes we can remember the
  # order and force this as model order.
  assert(output == "Person::Last   Name:bond;Name:james" or output == "Person::Name:james;Last   Name:bond")
  got_person = get(Person, output)
  # If all went well, we should GET back what we PUT.
  assert(got_person.name == "james" and got_person.last_name == "bond")
 

def constrained_lens_object_test():
  """
  Here we show how the user can constrain valid attributes of a LensObject.
  """
  return # TODO
  

def advanced_lens_object_test() :
  # Ref: http://manpages.ubuntu.com/manpages/hardy/man5/interfaces.5.html
  INPUT = """
iface eth0-home inet static
   address 192.168.1.1
   netmask 255.255.255.0
   gateway  67.207.128.1
   dns-nameservers 67.207.128.4 67.207.128.5
   up flush-mail

auto lo eth0
# A comment
auto eth1 
"""

  class NetworkInterface(LensObject) :
    
    __lens__ =  "iface" + WS(" ") + Keyword(additional_chars="_-", is_label=True) + WS(" ") + \
                Keyword(label="address_family") + WS(" ") + Keyword(label="method") + NL() + \
                ZeroOrMore(
                  KeyValue(WS("   ") + Keyword(additional_chars="_-", is_label=True) + WS(" ") + Until(NL(), type=str) + NL())
                )
    
    def __init__(self, **kargs) :
      for key, value in kargs.iteritems() :
        setattr(self, key, value)

    def _map_label_to_identifier(self, label) :
      return label.replace("-","_")
    
    def _map_identifier_to_label(self, attribute_name) :
      return attribute_name.replace("_", "-")


  test_description("Testing NetworkInterface")
  GlobalSettings.check_consumption = False
  interface = get(BlankLine() + NetworkInterface, INPUT)
  interface.cheese_type = "cheshire"
  interface.address = "bananas"
  output = put(interface) 

  # Try creating from scratch.
  interface = NetworkInterface(address_family="inet", method="static", dns_nameservers="1.2.3.4 1.2.3.5", netmask="255.255.255.0")
  output = put(interface, label="wlan3")
 
  #
  # Now lets create a class to represent the whole configuration.
  #

  class InterfaceConfiguration(LensObject) :
    __lens__ = ZeroOrMore(NetworkInterface | BlankLine() | HashComment())

    # TODO: Working here - need to add aggregate container support.

  #config = get(InterfaceConfiguration, INPUT)  

  GlobalSettings.check_consumption = True

def init_test():
  """
  Just a few tests to figure out how we can use __new__ in object creation.
  """
  # What we want:
  #  Want to create an object with initial state regardless of constructor
  #  args.

  class Person(object):
   
    age = 10

    def __new__(cls, *args, **kargs) :
      # It seems to me the args are passed only to allow customisation based
      # on them, since they are then passed to __init__ following this call in
      # typical creation.
      
      # Create the instance, also passing args - since may also be used for
      # customisation.
      self = super(Person, cls).__new__(cls, *args, **kargs)
      # Initialise some variables.
      self.name = None
      self.surname = None
      self.age = 3

      # Return the instance.
      return self
    
    def __init__(self, name, surname):
      d("Constructor called")
      self.name, self.surname = name, surname
    
    def __str__(self) :
      return "[%s, %s]" % (self.name, self.surname)


  person = Person("john", "smith")
  assert(person.name == "john" and person.surname == "smith")
  person = Person.__new__(Person)
  assert(person.name == None and person.surname == None)

  # So it seems python falls back on class var if obj var of same name not found.
  d(person.__class__.__dict__)
  d(person.age)
  d(person.__class__.age)
