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
#   Some tests that serve as more complex examples
#
from pylens import *
from pylens.debug import d # Like print(...)


def complex_class_test() :
  """
  This is an example of how we could embedded lenses within classes to
  manipulate the widely used interfaces.conf file to configure network
  interfaces of a UNIX systems.

  Note that it does not aim to be complete, just a demonstration of how you
  could compose such a mapping.
  """
 
  INPUT = """iface eth0-home inet static
   address 192.168.1.1
   netmask 255.255.255.0
   gateway  67.207.128.1
   dns-nameservers 67.207.128.4 67.207.128.5
   up flush-mail

auto lo eth0
# A comment
auto eth1 
"""

  # First we define a class to represent the iface stanza.  I break it up a
  # little to make it clearer.
  class NetworkInterface(LensObject) :
    
    # Some component lenses.
    indent = WS("   ")
    interface_attribute = KeyValue(indent + Keyword(additional_chars="_-", is_label=True) + WS(" ") + Until(NL(), type=str) + NL())
    
    # Put it all together.
    __lens__ =  "iface" + WS(" ") + Keyword(additional_chars="_-", is_label=True) + WS(" ") + \
      Keyword(label="address_family") + WS(" ") + Keyword(label="method") + NL() + \
      ZeroOrMore(interface_attribute)
    
    def __init__(self, **kargs) :
      """A simple constructor, which simply store keyword args as attributes."""
      for key, value in kargs.iteritems() :
        setattr(self, key, value)

    # Define label mappings, so labels such as "dns-nameservers" are mapped to and
    # from a valid python identifier such as "dns_nameservers" and can
    # therefore be manipulated as object attributes.
    def _map_label_to_identifier(self, label) :
      return label.replace("-","_")
    
    def _map_identifier_to_label(self, attribute_name) :
      return attribute_name.replace("_", "-")

  # Now we can define a class to represent the whole configuration, such that
  # it will contain NetworkInterface objects, etc.

  class InterfaceConfiguration(LensObject) :
    auto_lens = Group("auto" + WS(" ") + List(Keyword(additional_chars="_-", type=str), WS(" "), type=None) + WS("") + NL(), type=list, name="auto_lens")
    __lens__ = ZeroOrMore(NetworkInterface | auto_lens | HashComment() | BlankLine())

    interfaces = Container(store_items_of_type=[NetworkInterface], type=dict)
    auto_interfaces = Container(store_items_from_lenses=[auto_lens], type=list)
  
  if True:
    test_description("GET InterfaceConfiguration")
    config = get(InterfaceConfiguration, INPUT)
    assert_equal(config.interfaces["eth0-home"].address, "192.168.1.1")
    assert_equal(config.auto_interfaces[0][1],"eth0")
    assert_equal(len(config.auto_interfaces),2)
    
    test_description("PUT InterfaceConfiguration")
    config.interfaces["eth0-home"].netmask = "bananas"
    config.auto_interfaces[0].insert(1,"wlan2")
    output = put(config)
    assert_equal(output, """iface eth0-home inet static
   address 192.168.1.1
   gateway  67.207.128.1
   dns-nameservers 67.207.128.4 67.207.128.5
   up flush-mail
   netmask bananas

auto lo wlan2 eth0
# A comment
auto eth1 
""")
  
  test_description("CREATE InterfaceConfiguration")
  GlobalSettings.check_consumption = True
  interface = NetworkInterface(address_family="inet", method="static", dns_nameservers="1.2.3.4 1.2.3.5", netmask="255.255.255.0")
  interface.some_thing = "something or another"
  config = InterfaceConfiguration()
  config.interfaces = {"eth3":interface}
  config.auto_interfaces = [["eth0"], ["wlan2", "eth2"]]
  
  output = put(config)
  assert_equal(output, """iface eth3 inet static
   dns-nameservers 1.2.3.4 1.2.3.5
   some-thing something or another
   netmask 255.255.255.0
auto eth0
auto wlan2 eth2
""")



def debctrl_test() :
  """An example based on an example from the Augeas user guide."""

  # As a whole, this is a fairly complex lens, though as you work though it you
  # should see that the steps are fairly consistant.
  # This lens demonstrates the use of labels and the auto_list lens modifier. I
  # also use incremental testing throughout, which should help you to follow
  # it.

  DEB_CTRL = """Source: libconfig-model-perl
Section: perl
Maintainer: Debian Perl Group <pkg-perl-maintainers@xx>
Build-Depends: debhelper (>= 7.0.0),
               perl-modules (>= 5.10) | libmodule-build-perl
Build-Depends-Indep: perl (>= 5.8.8-12), libcarp-assert-more-perl,
                     libconfig-tiny-perl, libexception-class-perl,
                     libparse-recdescent-perl (>= 1.90.0),
                     liblog-log4perl-perl (>= 1.11)
"""

 

  # We build up the lens starting with the easier parts, testing snippets as we go.
  # Recall, when we set is_label we imply the lens has type=str (i.e is a STORE
  # lens)
  simple_entry_label =  Literal("Source", is_label=True)     \
                      | Literal("Section", is_label=True)    \
                      | Literal("Maintainer", is_label=True)

  #
  # Some general lenses for non-store artifacts of the string structure.
  #
  colon = WS("") + ":" + WS(" ", optional=True)
  comma_sep = WS("", indent_continuation=True) + "," + WS("\n  ", indent_continuation=True)
  option_sep = WS(" ", indent_continuation=True, optional=True) + "|" + WS(" ", indent_continuation=True, optional=True)


  #
  # simple_entry lens
  #

  # We lazily use the Until lens here, but you could parse the value further if you liked.
  # Note, auto_list unwraps a list if there is a single item, for convenience.
  # It is useful when we wish to associated a single item with a labelled
  # group.
  simple_entry = Group(simple_entry_label + colon + Until(NewLine(), type=str) + NewLine(), type=list, auto_list=True)

  # Test the simple_entry lens
  got = simple_entry.get("Maintainer: Debian Perl Group <pkg-perl-maintainers@xx>\n")
  
  # Just to highlight the effect of auto_list on a list type lens.
  if simple_entry.options.auto_list : 
    assert_equal(got, "Debian Perl Group <pkg-perl-maintainers@xx>")
  else :
    assert_equal(got, ["Debian Perl Group <pkg-perl-maintainers@xx>"])
    
  # An insight into how pylens stores meta data on items to assist storage.
  assert_equal(got._meta_data.label, "Maintainer")
  
  # Now try to PUT with the lens.
  # Notice how, since we are creating a new item with the lens, we must pass a
  # label to the lens, which is considered out-of-band of the item (i.e. it is
  # meta data).
  assert_equal(simple_entry.put("some value", label="Source"), "Source: some value\n")


  #
  # depends_entry lens
  #

  # Note the order of these: longest match first, since they share a prefix.
  depends_entry_label = Literal("Build-Depends-Indep", is_label=True)     \
                      | Literal("Build-Depends", is_label=True)
  
  # Here is an interesting lens, so let me explain it.
  # Each dependancy may be either a single application or a list of alternative
  # applications (separated by a '|'), so we use an List lens and set it as an
  # auto_list.
  # Since the application may have an optional version string, we store the application
  # info in a dict using labels for the app name and version string.
  package_options = List(
                      Group(
                        Word(alphanums+"-", init_chars=alphas, label="name") +
                        Optional(WS(" ") + "(" + Until(")", label="version") + ")"),
                        type=dict
                      ),
                      option_sep,
                      auto_list=True,
                      type=list,
                    )
  
  got = package_options.get("perl-modules (>= 5.10) | libmodule-build-perl") 
  assert_equal(got, [{"name":"perl-modules", "version":">= 5.10"}, {"name":"libmodule-build-perl"}])
  # Then test auto_list ensures the list is unwrapped for a single item.
  assert_equal(package_options.get("perl-modules (>= 5.10)"), {"name":"perl-modules", "version":">= 5.10"})
  
  assert_equal(package_options.put({"version":"3.4", "name":"some-app"}), "some-app (3.4)")
  assert_equal(package_options.put([{"version":"3.4", "name":"some-app"}, {"version":"< 1.2", "name":"another-app"}]), "some-app (3.4) | another-app (< 1.2)")

  # Now we wrap the package options in a comma separated list.  Notice how we do
  # not set the type to list, since we wish these items to be stored in a higher
  # level list, to avoid excessive list nesting.
  depends_list = List(package_options, comma_sep)

  # It might be over the top, but let's make sure this part works too.
  # Note that, for the isolated test of this lens we must set a type on it,
  # otherwise the sub-lenses will have nothing in which to store their extracted
  # items.
  depends_list.type = list
  got = depends_list.get("""debhelper (>= 7.0.0) | cheese,\n \t  perl-modules (>= 5.10) , libmodule-build-perl | monkey (1.2)""")
  assert_equal(got, [
    [{"name":"debhelper", "version":">= 7.0.0"}, {"name":"cheese"}],
    {"name":"perl-modules", "version":">= 5.10"},    # Not in list due to auto_list.
    [{"name":"libmodule-build-perl"}, {"name":"monkey", "version":"1.2"}],
  ])
  
  # Now lets try to PUT (actually CREATE a new) our abstract structure into a string.
  output = depends_list.put([
    [{"name":"beans", "version":">= 1.2"}, {"name":"eggs"}, {"name":"spam", "version":"<= 2.4"}],
    {"name":"cheese", "version":"3.3"},
  ])
  assert_equal(output, "beans (>= 1.2) | eggs | spam (<= 2.4),\n  cheese (3.3)")
  
  # Remember to remove the type now that it has been tested in isolation.
  depends_list.type = None  

  # Now put the dependancy entry togather.
  depends_entry = Group(depends_entry_label + colon + depends_list + WS("") + NewLine(), type=list)
  
  # And now we have our final lens.
  lens = Repeat(simple_entry | depends_entry, type=dict, alignment=SOURCE)
  
  # This names all of the lenses based on their variable names, to improve clarity of debug logs.
  auto_name_lenses(locals())
  
  # Now lets get the config file snippet as an abstract form we can easily
  # manipulate.
  got = lens.get(DEB_CTRL)
  
  # Now let's modify it a bit
  del got["Build-Depends"]
  
  # Lets insert some more dependancies.
  got["Build-Depends-Indep"].insert(2, 
    [{"name":"cheese", "version":"3.3"}, {"name":"spam"}]
  )
  output = lens.put(got)
  
  # Now lets check the output.
  assert_equal(output, """Source: libconfig-model-perl
Section: perl
Maintainer: Debian Perl Group <pkg-perl-maintainers@xx>
Build-Depends-Indep: perl (>= 5.8.8-12), libcarp-assert-more-perl,
                     cheese (3.3) | spam, libconfig-tiny-perl,
                     libexception-class-perl,
                     libparse-recdescent-perl (>= 1.90.0),
  liblog-log4perl-perl (>= 1.11)
""")

  # Now let's finish off by creating some output from scratch (i.e. using
  # default values of all non-store lenses rather than any original input.
  data = {
    "Source": "Just a simple entry",
    "Build-Depends-Indep": [
      [{"name":"cheese", "version":"1.2"}, {"name":"nbdebug"}],
      {"name":"someapp", "version":"<= 1.1"},
    ]
  }
  output = lens.put(data)
  assert_equal(output, """Source: Just a simple entry\nBuild-Depends-Indep: cheese (1.2) | nbdebug,\n  someapp (<= 1.1)\n""")



# Useful for testing an installation.
if __name__ == "__main__" :
  debctrl_test()
