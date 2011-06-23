Pylens - Object Serialisation through a Lens
====================================================

Author: Nick Blundell (http://www.nickblundell.org.uk)

Here is the Problem
-----------------------------------------------------

Suppose that you have some structure within some string (think of a UNIX
configuration file) that you wish to manipulate programmatically (perhaps you
are automating the task of wider system configuration) but you do not wish to
destroy non-semantic artifacts within the string that are important to still
allow for manual maintenance, such as comments, whitespace
list delimiters, etc.  In other words, you wish to make *surgical* changes to
the string, leaving undisturbed those parts that do not concern your
alteration.

This is where the concept of bi-directional programming (see references below)
can really help us. Here we specify a *lens*, which is a parser that works not only in the
classical sense to parse a
string into an abstract model (for easy manipulation) but that can 
also put back (i.e. unparse) our modified structure into an appropriate string
form.

The Approach of pylens
-----------------------------------------------------

The pylens framework closely relates the concept of a lens with python, such
that lenses may be defined simply as python code (greatly inspired by
`pyparsing <http://pyparsing.wikispaces.com/>`_) and may be mapped to and from python
structures, such as lists, dicts, and classes.

This resembles a special kind of serialisation where we can extract python
structures from arbitrary string structures, easily modify the structure, and
then put the model back into a string structure that embodies our changes.

Example
-----------------------------------------------------

The library is used as follows::
  
  from pylens import *

  # Define your lens (a special kind of grammar).
  lens = ... define your lens ...

  # Extract some structured string into a python structure.
  data = lens.get("some string structure")

  # Manipulate your data using standard python.
  ...

  # Then weave your changes back into the string format.
  output = lens.put(data)

I will work on some better docs very soon, but for now you can look in the following
source files:

For some examples of how to use pylens, see `Examples
<https://github.com/blundeln/pylens/tree/master/examples>`_

For more examples, see the extensive unit tests and longer tests in the following files::

  testing/tests.py
  pylens/*_lenses.py

Limitations
-----------------------------------------------------

Note that, the initial aim of this project is to see if we can create some
richer abstractions of data (i.e. using native language objects) for use with
lenses, but that, since we do not use an FSA like Augeas and Boomerang,
ambiguity checking is not supported, though I'm interested in exploring
how we can implement some kind of certainty of non-ambiguity into the
framework, if not full ambiguity checking.  pylens does not claim to be a full
typed checked system, and leaves sanity checking down to the lens designer.

The main idea here is to increase flexibility of the framework at the price of
weaker type-checking, leaving part of that responsibility to the lens authors.

Status
-----------------------------------------------------

For an informal TODO list see the TODO file:
https://github.com/blundeln/pylens/blob/master/TODO

The Theory
-----------------------------------------------------


For more details on the theory see the work
relating to lenses/bi-directional-programming of Nate Foster et al. (links
below).

Pylens is Inspired By
------------------------------------------------------

* Lens theory: Nate Foster, et al.: http://www.cs.cornell.edu/~jnfoster/
* Functionality: http://augeas.net/
* Ease of parser definition: pyparsing: http://pyparsing.wikispaces.com/
* Design: The clean design of Yean, by Markus Brueckner: http://www.slash-me.net/dev/snippets/yeanpypa/documentation.html
