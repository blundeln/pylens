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


def fundamentals_test() :

  """
  If you are familiar with parsing of strings, then you will quickly pick up the
  concept of bi-directional programming (i.e. essentially parsing and then
  unparsing strings to and from, in this case, some python structure).  A lens
  defines a grammar (or part of) to define this bi-directional transformation.

  An important concept of a lens is that we need to define which parts of the
  original string structure we are interested in manipulating in our python
  structure and which we are not.  For example, later on we will write a lens to
  extract words from some comma-separated list structure into a python list,
  disregarding uninteresting artifacts such as delimiters and whitespace.
  
  However, when we later wish to recreate the string structure to include our
  pythonic modifications, we would like to restore those non--python-model
  artifacts where possible and create new such artifacts where we have added to
  the original string structure (i.e. we appended a list, so now will need to
  generate a new comma and perhaps some space when reflecting that change in the
  string structure).
  
  In lens-speak we talk about converting structures between concrete (i.e.
  original, flat string form) and abstract forms (i.e. native language types and
  classes in which we can easily manipulate the data).

  Since the grammar works for both parsing and un-parsing, we describe parsing
  as GETing (the abstract structure) and un-parsing as PUTing (the modified
  abstract structure back into an appropriate concrete structure).
  """
  
  # The following lens, though in itself not so interesting, demonstrates the
  # interface of a lens and some fundamental properties.  This lens will GET
  # and PUT a single character if it falls within the set of 'nums' (simply a
  # predefined set of chars '1234..89'); otherwise it will fail.
  #
  # There are two main types of lenses: those that STORE items into the
  # abstract structure and those that discard them (i.e. NON-STORE).  Whenever
  # we set a type on a lens it becomes a STORE lens.  In this case, we wish to
  # store the matched character as a python int, an obvious choice if we are
  # dealing with the set of digit characters.
  lens = AnyOf(nums, type=int)
  
  # So when we call GET on the lens with an input string "1" we extract a 1.
  my_number = lens.get("1")
  assert_equal(my_number,  1)

  # Then, perhaps after modifying the piece of data we extracted, we PUT it
  # back (into its original string form).
  my_number += 5
  assert_equal(lens.put(my_number),  "6")

  # Okay, that doesn't look too useful yet, but stick with me.
  #
  # Now let's see how a similar though non-store lens behaves.  I will explain the 'default' arg shortly.
  lens = AnyOf(alphas, default="x")   # alphas is the set of alphabhetic chars.

  # Since this is a non-store lens, we extract nothing for our abstract
  # structure (i.e. we get None), though the character will still be consumed from the concrete
  # input string.
  assert_equal(lens.get("b"),  None)
  
  # Now, we have no abstract item to PUT (i.e. None as first arg), though if we
  # pass the original input string as the second arg it will be copied to generate
  # new (concrete) output for this lens.
  assert_equal(lens.put(None, "b"),  "b")

  # But suppose we have no original input, since we may be extending the
  # concrete string somehow.  In this case, if the lens has a default value set,
  # it will output that; otherwise it will fail.
  # In the lens literature, this special case of PUT is referred to as CREATE,
  # since we are creating new artifacts in the concrete structure.
  assert_equal(lens.put(None),  "x")

  # These are the fundamentals of this lens framework and their usefulness
  # will become very apparent when we aggregate smaller lenses into more
  # complex ones, much like building up a BNF grammar.
 

def aggregating_lenses_test() :
  
  # We can use the And lens to concatenate several other lenses.  Note that, here we
  # specify the And's type as a python list, otherwise we will have nothing into
  # which the extracted values of the two AnyOf lenses can be stored - which
  # will give an error.
  #
  # Also, here we introduce the Literal lens, a very simple lens which conveniently handles literal (i.e.
  # constant strings that we are usually not interested in extracting into our
  # model).
  lens = And(AnyOf(alphas, type=str), Literal("--=--"), AnyOf(nums, type=int), type=list)
  
  # Get the list from our input string.
  my_list = lens.get("b--=--3")
  assert_equal(my_list,  ["b",3])

  # Modify it
  my_list[0] = "n"
  my_list[1] -= 2

  # Put it back into string form.
  assert_equal(lens.put(my_list),  "n--=--1")

  # Or, CREATE afresh without first GETing
  assert_equal(lens.put(["g", 7]),  "g--=--7")

  # We might also wish to repeat such a lens indefinitely.
  repeated_lens = Repeat(lens, type=list)
  assert_equal(repeated_lens.get("d--=--4f--=--8s--=--2"),  [["d", 4], ["f", 8], ["s", 2]])

def grouping_test():

  # Note that there are some syntax shortcuts (a la pyparsing) we can use when
  # defining lenses.

  # Here the And lens is implied when using the addition operand: A + B + C ->
  # And(A, B, C); and the string "--=--" is automatically coerced to the
  # lens Literal("--=--").
  lens_part = AnyOf(alphas, type=str) + "--=--" + AnyOf(nums, type=int)
  
  # Since the previous lens was not defined explicitly as And, we could not
  # set its type to list.  We could either do this like: lens_part.type = int;
  # or it can be more convenient to use the Group lens, this this, which
  # closes part of a larger lens within its own container:
  lens = Group(AnyOf(alphas, type=str) + "--=--" + AnyOf(nums, type=int), type=list)
  
  # Let's confirm this works identically to our previous lens.
  assert_equal(lens.get("b--=--3"),  ["b",3])


def conditional_lenses_test() :

  # But we also need to allow for alternative branching in realistic grammar
  # parsing (and unparsing), so here we can use the Or lens.
  # Here the syntax A | B | C  is shorthand for Or(A, B, C).
  lens = Repeat(AnyOf(nums, type=int) | AnyOf(alphas, type=str) | "*", type=list)
 
  # So we store ints or alphabhetical chars - but not the (non-store)
  # asterisks.
  my_list = lens.get("1a*2b*3**d*45*6e78")
  assert_equal(my_list,  [1, 'a', 2, 'b', 3, 'd', 4, 5, 6, 'e', 7, 8])

  # Note that the order of lenses is important when using Or: in both the GET
  # and PUT direction, the first-most lens is favoured, so as a general rule of
  # thumb you should put the longest matching lenses first if there is any
  # possibility of overlap in what they match (i.e. one lens may match what is
  # the prefix of what another lens matches), for example: 'cheese' | 'cheeseshop' should be
  # re-ordered to 'cheeseshop' | 'cheese'.  This is ultimately down to the
  # behaviour that the lens author desires.

  # Now let's modify our list to demonstrate how non-store input is preserved - note
  # where the asterisks are in the modified output string: where they were in
  # the input string.
  my_list[0] = 'x'
  my_list[1] = 9
  my_list[4] += 4 # 3 -> 7
  assert_equal(lens.put(my_list),  "x9*2b*7**d*45*6e78")
  
  # In practical terms, this translates to the preservation of important
  # artifacts of, say, configuration files, such as comments, whitespace,
  # indentation, etc. that, whilst not important to us when modifying the
  # semantics of the structure, are extremely important for manual maintenance of
  # such files --- in fact, this is the main motivation behind the theory of
  # lenses, namely how to make surgical changes to concrete structures to
  # reflect semantic changes.




def combining_characters_test():

  # Sometimes we wish to combine aggregated single character lenses into a
  # string, which can be done with the combine_chars argument of an appropriately
  # constructed lens of type list.
  lens = Repeat(AnyOf(alphas, type=str) + "--=--" + AnyOf(nums, type=str), type=list, combine_chars=True)
  assert_equal(lens.get("g--=--2n--=--4c--=--6"),  "g2n4c6")
  assert_equal(lens.put("b8m2s8l2"),  "b--=--8m--=--2s--=--8l--=--2")

def useful_lenses_test() :

  # It is very easy to extend pylens with new lenses but I've created a few
  # already based on common parser patterns and on those useful parsing classes
  # you can find in pyparsing.

  # Here is a demo of some, explained below.
  lens = Repeat(Whitespace("\t") + Word(alphanums+"_", init_chars=alphanums, type=str) + WS("", optional=True) + NewLine(), type=list)
  variables = lens.get("\tvariable_1    \n     variable_2\n variable_3\n")
  assert_equal(variables,  ["variable_1", "variable_2", "variable_3"])
  # Whitespace(default_output_when_creating): Optionally matches one or more common whitespace chars.
  # WS: Just a shortcut alias of Whitespace.
  # Word(body_chars[, init_chars]): for matching keywords of certain body and initial characters.
  # NewLine(): Matches the end of a line but also optionally the end of the input string.

  # And let's modify then put back our list of variable names.
  variables.extend(["variable_4", "variable_5"])
  output = lens.put(variables)
  assert_equal(output,  "\tvariable_1    \n     variable_2\n variable_3\n\tvariable_4\n\tvariable_5\n")
  


def simple_list_test() :
  # Let's define some sample input.
  INPUT_STRING = "monkeys,\tmonsters,\t rabbits, frogs, badgers"
  
  # Here is an example of the List lens, which allows us to specify a lens for
  # the item and a lens for the delimiter.  In this case we wish to extract the
  # animal names as strings to store in a python list, whereas we wish to discard the
  # whitespace and delimiters.
  lens = List(Word(alphas, type=str), WS("") + "," + WS(" ", optional=True), type=list)
  got = lens.get(INPUT_STRING)
  assert_equal(got,  ["monkeys", "monsters", "rabbits", "frogs", "badgers"])

  # But the idea of a lens (a bi-directional parsing element) is that once we
  # have modified that abstract model, we can write it back, preserving
  # artifacts of the original string, or creating default artifacts for new
  # data.
  del got[1]    # Remove 'monsters'.
  got.extend(["dinosaurs", "snails"])  # Throw a few more in.
  output = lens.put(got)

  # Notice that additional spacing is preserved in
  # the outputted list and that the new items on the end use default spacing
  # that the Whitespace lenses were initialised with (i.e. no space before the
  # comma and a single space after).
  assert_equal(output,   "monkeys,\trabbits,\t frogs, badgers, dinosaurs, snails")


def more_complex_structure_test() :
  # Let's define out input structure.
  INPUT_STRING = """
  people: [bill, ben]

  animals: [snake,tiger,monkey]
  food: [beans, eggs]\n"""

  # This lens defines the comma separator of the list lens we will use it in
  # shortly.  For convenience, the first arg of Whitespace is the default value to
  # use when CREATING with this lens.
  comma_separator = WS("") + "," + WS(" ", optional=True)
  
  # This defines the comma-separated list lens, specifying that we wish to store
  # the items (which contain only the alphabhetic characters) as strings.
  item_list = List(Word(alphas, type=str), comma_separator)
  
  # Recall, WS is simply an abbreviation of the Whitespace lens.  Note the use
  # of is_label on the Word lens, which effectively sets this lenses matching
  # string as the label of the current Group (type=str is implied when we set
  # is_label on a lens).
  entry = Group(WS("  ") + Word(alphas, is_label=True) + WS("") + ":" + WS("") + "[" + item_list + "]" + NewLine(), type=list)

  # Test the parts - its always good to work incrementally.
  assert_equal(entry.get("  something: [a , b,c,d]\n"),  ["a","b","c","d"])
 
  # Now put the lens together, and set the type to dict, so we can make use of
  # the labels of the key lens in entry.  Note that, especially with dictionaries, there are a few
  # possibilities of realigning them with the source: based on label strings,
  # original location within the source, and abstract ordering (i.e. arbitrary
  # for python dicts).  TODO: I will write more on alignment soon.
  lens = OneOrMore(entry | BlankLine(), type=dict, alignment=SOURCE)
  
  # This is a useful function for debugging lenses, which simply scans the
  # local variables for lenses and then sets each lens' debugging name to the
  # variable name (e.g. item_list.name = "item_list")
  auto_name_lenses(locals())

  # Great.  Now let's GET it, modify it, then PUT it back as a string.
  got = lens.get(INPUT_STRING)
  # Excellent, we have it as a python structure.
  assert_equal(got,  {'food': ['beans', 'eggs'], 'animals': ['snake', 'tiger', 'monkey'], 'people': ['bill', 'ben']})
  got["newthing"] = ["thinga", "thingb"]
  output = lens.put(got)
  assert_equal(output,  """
  people: [bill, ben]

  animals: [snake,tiger,monkey]
  food: [beans, eggs]
  newthing:[thinga, thingb]\n""")


def mapping_lenses_to_classes_test():
  """
  We have seen how we can use list and dict container types to store items
  extracted by a lens but we can also easily define
  classes that map to lenses, and we can use these as elements of larger lenses,
  allowing us to (surgically) manipulate potentially complex structured files in a
  flexible class model.

  This can be thought of as a special form of serialisation whereby a class
  defines the lens that it uses for serialisation to and from the flat string
  structure.
  """

  # Define our Person class, which internally defines its lens, using the
  # special __lens__ attribute.
  class Person(LensObject) :
    # We define the lens that maps an element of some grammer to and from this
    # class.  The KeyValue lens is a simple wrapper of the Group to set
    # default lens values that are useful storing key-value structures - look
    # at the code.
    __lens__ = "Person::" + List(
      KeyValue(Word(alphas+" ", is_label=True) + ":" + Word(alphas+" ", type=str)),
      ",",
    )
   
    # If we declare attributes of our model, we can (a) restrict lens storage
    # only to these and (b) define the order of which item to PUT first when
    # CREATEing, otherwise order would be arbitrary..
    # If we don't declare these, the lens can use any (viable) attribute of the
    # object for storing or putting items.
    name = Attribute()
    last_name = Attribute()

    # Example of a simple function.
    def __init__(self, name, last_name) :
      self.name, self.last_name = name, last_name


  # Extract a person instance from the string.  Note how the field with label
  # "Last Name" gets mapped automatically to the attribute last_name.  This
  # default behaviour can be customised by overloading certain functions of
  # LensObject
  person = get(Person, "Person::Name:Nick,Last Name:Blundell")
  assert_equal(person.name,  "Nick")
  assert_equal(person.last_name,  "Blundell")

  # We can use the class as part of a larger lens now.
  lens = List(Person, ";", type=list)
  
  # Here extract a python list of Person instances.
  people = lens.get("Person::Name:Nick,Last Name:Blundell;Person::Last Name:Camus,Name:Albert")
  assert_equal(people[0].name,  "Nick")
  assert_equal(people[1].last_name,  "Camus")

  # Let's alter our abstract model, then put it back as a string.
  people.insert(1,Person("Fred", "Flintstone"))
  output = lens.put(people)
  
  # Note, here, that when we CREATE the new person, Fred, the order in which
  # 'Name' and 'Last Name' would be arbitrary should we not have optionally
  # declared those attributes, name and last_name, within our class.
  #
  # In the case where we modify an existing (i.e. GOT) Person the labelled items
  # will be aligned according to the original source, compare the order of Camus with
  # Blundell.
  assert_equal(output,  "Person::Name:Nick,Last Name:Blundell;Person::Name:Fred,Last Name:Flintstone;Person::Last Name:Camus,Name:Albert")
 
  # For more details on usage, until I add to this documentation, please see
  # the source files, which contain lots of testing code to demonstrate
  # different things.

#
# TODO: Alignment mode examples.
# TODO: Until, auto_list
# TODO: Aggregate containers.
# TODO Recursion examples
