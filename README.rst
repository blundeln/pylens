Pylens - Object Serialisation through a Lens
====================================================

Author: Nick Blundell (http://www.nickblundell.org.uk)

.. TOC

Here is the Problem
-----------------------------------------------------

Suppose that you wish to programatically change part of a potentially complex
structure stored within a string (e.g. perhaps a UNIX configuration file) such that
the rest of the structure is left untouched, perhaps things like comments and
spacing, to still allow for manual maintenance.

If we parsed such a structure using a typical parser, we will certainly
extract an abstract model of the structure that we can work with and change,
but the problem comes when we wish to write those changes back out as a
string, since all of the non-semantic artifacts (e.g. whitespace, comments,
etc.) get lost in the parsing process.

To put it another way, we wish in certain circumstances to make *surgical* changes to
the string, leaving undisturbed those parts that do not concern our
alteration, and therefore without us stomping over artifacts that may be
important to other co-operating systems or manual editors.

This is where the concept of bi-directional programming (see references below
for more of the background) can really help us. Here we specify a so-called *lens*,
which is a parser that works not only in the classical sense to parse a string
into an abstract model (for easy manipulation) but that can also be used to weave
our modified structure back into the original string.

The lens concept is a generalisation of the classic view-update problem often
found in database technology, where we wish to modify a simplified view of
some data and have the changes reflected in the data proper.

The Approach of pylens
-----------------------------------------------------

The pylens framework closely relates the concept of a lens with python code, such
that lenses may be defined simply in python (greatly inspired by
`pyparsing <http://pyparsing.wikispaces.com/>`_) and may be mapped to and from python
structures, such as lists, dicts, and classes.

This resembles a special kind of serialisation where we can extract python
structures from arbitrary string structures, easily modify the structure, and
then surgically put the model back into the original string structure such
that it embodies our changes.

Since lenses are represented as python classes, it is straightforward to
extend their functionality.

Example
-----------------------------------------------------

Suppose we have a config file that looks like this, and let's assume it has
been read into a variable **CONFIG_STRING**::

  # Auto interfaces.
  auto lo eth0

  allow-hotplug eth1

  # Define mapping for eth0.
  mapping eth0
       # Mapping script
       script /usr/local/sbin/map-scheme
       map HOME eth0-home
       map WORK eth0-work

  # eth0 home configuration.
  iface eth0-home inet static
       address 192.168.1.1
       netmask 255.255.255.0
       up flush-mail

and we wish to programatically make some changes, so that it becomes this (the
changes are highlighted with square brackets)::

  # Auto interfaces.
  auto lo [wlan0] eth0

  allow-hotplug eth1

  # Define mapping for eth0.
  mapping eth0
       # Mapping script
       script [/home/fred/map_script]
       map HOME eth0-home
       map WORK eth0-work

  # eth0 home configuration.
  iface eth0-home inet static
       address 192.168.1.1
       [dns-nameservers 192.168.1.4 192.168.1.5]
       netmask 255.255.255.0
       up flush-mail
  
  [iface wlan0 inet dhcp]

We use the pylens framework as follows::
  
  from pylens import *

  # Define our python model and a lens for mapping our model to
  # and from the string structure.
  class NetworkConfiguration(LensObject) :
    # Our definition of the lens which maps between the string structure and
    # this class - this will become clearer in the tutorials.
    __lens__ = ZeroOrMore(NetworkInterface | auto_lens | HashComment() | BlankLine())
    
    # We can add whatever functions we like for manipulating our class, such
    # as a constructor.
    def __init__(self, ...) :
      ...
  
  # Now extract our model's representation from the config string.
  net_config = get(NetworkConfiguration, CONFIG_STRING)

  # Then modify the structure using standard python.
  net_config.auto_interfaces[0].insert(1, "wlan0")
  net_config.interface_mappings["eth0"].script = "/home/fred/map_script"
  net_config.interfaces["eth0-home"].dns_nameservers = ["192.168.1.4", "192.168.1.5"]
  net_config.interfaces["wlan0"] = Interface(address_family="inet", method="dhcp")

  # Then weave the changes back into the original config string (i.e. change
  # only what needs to be changed, disturbing as little of the original config
  # string as possible).
  CONFIG_STRING = lens.put(net_config)


Documentation
-----------------------------------------------------

You can find online documentation for pylens here:
http://packages.python.org/pylens/

For more of a detailed insight into pylens, you might also wish to look at some of the
source files, which contain extensive testing code that works fully but which
has yet to be documented (e.g. recursion, etc.)::

  examples/*.py
  testing/tests.py
  pylens/*_lenses.py


Limitations
-----------------------------------------------------

Note that the initial aim of this project was to see if the concept of lenses
and bi-directional programming could be integrated more closely with a
language such as python, allowing rich models to be composed of classes and
other native types (e.g. strings, floats, lists, dicts, etc.), but this has
been achieved through compromise, since there is currently no validation of
lens behavedness (as you will find in the tool Augeas, referenced below),
which requires the expensive analysis of finite state automata.  Put simply, a
well-behaved lens will always adhere to the following rules::

  lens.get(lens.put(x)) == x
  lens.put(lens.get(y)) == y

I am interested in exploring how we can implement some kind of certainty of
behavedness into the framework, if not full ambiguity checking, but for now
sanity checking is left down to the lens author, though I have provided within the
framework aids to support the incremental development and testing of lenses,
which should help you to create something that works for you.

The Theory
-----------------------------------------------------

For more details on the theory and inspiration of pylens, please see the
following links.

* Lens theory: Nate Foster, et al.: http://www.cs.cornell.edu/~jnfoster/
* Functionality: http://augeas.net/
* Ease of parser definition: pyparsing: http://pyparsing.wikispaces.com/
* Design: The clean design of Yean, by Markus Brueckner: http://www.slash-me.net/dev/snippets/yeanpypa/documentation.html
