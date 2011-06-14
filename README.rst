Pylens - Object Serialisation through a Lens
====================================================

Author: Nick Blundell (http://www.nickblundell.org.uk)

This started of as an attempt to implement the extremely useful idea of lenses
(bi-directional parsers) within the context of object serialisation, with the
aim of simplifying lens definition and creating intuitive abstractions of data
in flat file formats (e.g. UNIX configuration files) within a native scripting
language such as python.

In a nutshell, we wish to serialise some object model to and from a flat file
with some arbitrary structure, such that changes are made surgically to those
files to reflect changes in the model (e.g. comments and whitespace are
preserved where possible to allow both automated and manual configuration).

For those familiar with `pyparsing <http://pyparsing.wikispaces.com/>`_, this is like pyparsing but it works in both
directions, for parsing *and* unparsing abstract models of data, whilst
keeping the idea of simple, in-language parser definition.

Usage
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

Status
-----------------------------------------------------

Work in progress: alpha stage

Note that, the initial aim of this project is to see if we can create some
richer abstractions of data (i.e. using native language objects) for use with
lenses, but that, since we do not use an FSA like Augeas and Boomerang,
ambiguity checking is not yet supported, though I'm interested in exploring
how we can implement some kind of certainty of non-ambiguity into the
framework, if not full ambiguity checking.  pylens does not claim to be a full
typed checked system, and leaves sanity checking down to the lens designer.

The main idea here is to increase flexibility of the framework at the price of
weaker type-checking, leaving part of that responsibility to the lens authors.

For an informal TODO list see the TODO file:
https://github.com/blundeln/pylens/blob/master/TODO

For more details on the theory see the work
relating to lenses/bi-directional-programming of Nate Foster et al. (links
below).

Pylens is Inspired By
------------------------------------------------------

* Lens theory: Nate Foster, et al.: http://www.cs.cornell.edu/~jnfoster/
* Functionality: http://augeas.net/
* Ease of parser definition: pyparsing: http://pyparsing.wikispaces.com/
* Design: The clean design of Yean, by Markus Brueckner: http://www.slash-me.net/dev/snippets/yeanpypa/documentation.html
