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

def debctrl_test() :
  """An example based on the Augeas user guide."""
  simple_entry_label =  Literal("Source", is_label=True)     \
                      | Literal("Section", is_label=True)    \
                      | Literal("Maintainer", is_label=True)

  colon = WS("") + ":" + WS(" ", optional=True)
  simple_entry = Group(simple_entry_label + colon + Until(NewLine(), type=str) + NewLine(), type=list, auto_list=True)
 
  # Note the order of these: longest match first, since they share a prefix.
  depends_entry_label = Literal("Build-Depends-Indep", is_label=True)     \
                      | Literal("Build-Depends", is_label=True)
  
  comma_sep = WS("", indent_continuation=True) + "," + WS("\n  ", indent_continuation=True)
  option_sep = WS(" ", indent_continuation=True, optional=True) + "|" + WS(" ", indent_continuation=True, optional=True)
  
  package_options = List(
                      Group(
                        Word(alphanums+"-", init_chars=alphas, label="name") +
                        Optional(WS(" ") + "(" + Until(")", label="version") + ")"),
                        type=dict
                      ),
                      option_sep, type=list
                    )
  
  # It is helpful to test the components incrementally.
  package_options.get("perl-modules (>= 5.10) | libmodule-build-perl") 

  depends_list = List(package_options, comma_sep, type=list) # XXX
  
  # It is helpful to test the components incrementally.
  depends_list.type = list # Just for testing we make this a container type.
  test_description("HERE")
  auto_name_lenses(locals())
  got = depends_list.get("""debhelper (>= 7.0.0) | cheese,                                                                                                                 
                 perl-modules (>= 5.10) | libmodule-build-perl                                                                                         
Build""")
  # XXX: First item is not being wrapped in a list!
  d(got[0])
  depends_list.type = None  
  return

  depends_entry = Group(depends_entry_label + colon + depends_list + WS("") + NewLine(), type=list)
  
  # Test
#  depends_entry.get("""Build-Depends: debhelper (>= 7.0.0),                                                                                                                 
#                 perl-modules (>= 5.10) | libmodule-build-perl                                                                                         
#Build""")
#  return
  
  
  lens = Repeat(simple_entry | depends_entry, type=dict, alignment=SOURCE)
  
  auto_name_lenses(locals())
  
  got = lens.get(DEB_CTRL)
  d(got)
  d("XXXXX: %s" % got["Build-Depends-Indep"])
  return
  del got["Build-Depends"]
  #got["Build-Depends-Indep"][1:2] = []

  output = lens.put(got)
  d(output)
