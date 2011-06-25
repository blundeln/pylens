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

Suppose we have a config file that looks like this::

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

and we wish to programatically make some changes so that it becomes (the
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
    __lens__ = [Our definition of the lens which maps
               between the string structure and this class]
    
    def __init__(self, ...) :
      ...
  
  # Extract our model's representation from the config string.
  config = get(NetworkConfiguration, CONFIG_STRING)

  # Modify the structure using standard python.
  config.auto_interfaces[0].insert(1, "wlan0")
  config.interface_mappings.script = "/home/fred/map_script"
  config.interfaces["eth0-home"].dns_nameservers = ["192.168.1.4", "192.168.1.5"]
  config.interfaces["wlan0"] = Interface(address_family="inet", method="dhcp")

  # Then weave the changes back into the original config string (i.e. change
  # only what needs to be changed, disturbing as little of the original config
  # string as possible).
  MODIFIED_CONFIG_STRING = lens.put(config)


I will work on some better docs very soon, but for now you can look in the following
source files:

For some examples of how to use pylens, see `Examples
<https://github.com/blundeln/pylens/tree/master/examples>`_

For more undocumented examples, see the extensive unit tests and longer tests in the following files::

  testing/tests.py
  pylens/*_lenses.py

Limitations
-----------------------------------------------------

Note that the initial aim of this project was to see if we could 
integrate more closely the concept of lenses and bi-directional
programming with a language such as python, allowing rich models to be
composed of classes and native types (e.g. strings, floats, lists, dicts,
etc.) but this has been achieved through compromise, since there is currently
no validation of lens behavedness, which requires the expensive analysis
of finite state automata.  You can read more about this in the theory
references below, and how it relates to ambiguity.

I am interested in exploring
how we can implement some kind of certainty of non-ambiguity into the
framework, if not full ambiguity checking, so for now sanity checking is
left down to the lens author and I have provided within the framework aids to
support the incremental development and testing of lenses.

The Theory
-----------------------------------------------------

For more details on the theory and inspiration of pylens, please see the
following links.

* Lens theory: Nate Foster, et al.: http://www.cs.cornell.edu/~jnfoster/
* Functionality: http://augeas.net/
* Ease of parser definition: pyparsing: http://pyparsing.wikispaces.com/
* Design: The clean design of Yean, by Markus Brueckner: http://www.slash-me.net/dev/snippets/yeanpypa/documentation.html
