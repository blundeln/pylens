Pylens - Object Serialisation through a Lens
====================================================

Author: Nick Blundell (http://www.nickblundell.org.uk)

This is an attempt to implement the extremely useful idea of lenses
(bi-directional parsers) within the context of object serialisation, with the
aim of simplifying lens definition and creating intuitive abstractions of data
in flat file formats (e.g. UNIX configuration files).

In a nutshell, we wish to serialise some object model to and from a flat file
with some arbitrary structure, such that changes are made surgically to those
files to reflect changes in the model (e.g. comments and whitespace are
preserved where possible to allow both automated and manual configuration).

For those familiar with pyparsing, this is like pyparsing but it works in both
directions, for parsing *and* unparsing abstract models of data, whilst
keeping the idea of simple, in-language parser definition.

Usage
-----------------------------------------------------

I will work on this, but for now, to get a feel for how it works, see the unit
tests and longer tests in the following files::

  pylens/*_lenses.py
  testing/tests.py

Status
-----------------------------------------------------

Work in progress: alpha stage

Note that, the initial aim of this project is to see if we can create some
richer abstractions of data (i.e. using native language objects) for use with
lenses, but that, since we do not use an FSA like Augeas and Boomerang,
ambiguity checking is not yet supported, though I'm interested in exploring
how we can implement some kind of certainty of non-ambiguity into the
framework, if not full ambiguity checking.

The main idea here is to increase flexibility of the framework at the price of
weaker type-checking, leaving part of that responsibility to the lens authors.

For more details see the work
relating to lenses/bi-directional-programming of Nate Foster et al. (link
below).

Pylens is Inspired By
------------------------------------------------------

* Lens theory: Nate Foster, et al.: http://www.cs.cornell.edu/~jnfoster/
* Functionality: http://augeas.net/
* Ease of parser definition: pyparsing: http://pyparsing.wikispaces.com/
* Design: The clean design of Yean, by Markus Brueckner: http://www.slash-me.net/dev/snippets/yeanpypa/documentation.html
