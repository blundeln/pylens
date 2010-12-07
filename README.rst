Pylens - Object Serialisation through a Lens
====================================================

Author: Nick Blundell (www.nickblundell.org.uk)

This is an attempt to implement the extremely useful idea of lenses
(bi-directional parsers) within the context of object serialisation, with the
aim of simplifying lens definition and creating intuitive abstractions of data
in flat file formats (e.g. UNIX configuration files).

In a nutshell, we wish to serialise some object model to and from a flat file
with some arbitrary structure, such that changes are made surgically to those
files to reflect changes in the model (e.g. comments and whitespace are
preserved where possible to allow both automated and manual configuration).

Status
-----------------------------------------------------

Work in progress: alpha stage

Note that, the initial aim of this project is to see if we can create some
richer abstractions of data (i.e. using native language objects) for use with
lenses, but that, since we do not use an FSA like Augeas and Boomerang,
ambiguity checking is not yet supported, though I'm interested in exploring
how we can implement some kind of certainty of non-ambiguity into the
framework, if not full ambiguity checking.  For more details see the work of
Nate Foster (link below).

Pylens is Inspired By
------------------------------------------------------

* Lens theory: Nate Foster, et al.: http://www.cs.cornell.edu/~jnfoster/
* Functionality: http://augeas.net/
* Ease of parser definition: pyparsing: http://pyparsing.wikispaces.com/
* Design: The clean design of Yean, by Markus Brueckner: http://www.slash-me.net/dev/snippets/yeanpypa/documentation.html
