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

def deb_test() :

  INPUT = """Build-Depends: debhelper (>= 7.0.0),
                 perl-modules (>= 5.10) | libmodule-build-perl,
                 perl (>= 5.8.8-12), \
               libcarp-assert-more-perl [!amd64],
                 libconfig-tiny-perl, libexception-class-perl | someapp | someotherapp (> 1.2),
                 libparse-recdescent-perl ( >= 1.90.0),
                 liblog-log4perl-perl (>= 1.11)  [i386]"""
  # In this case, a space effectively is also a space followed by a newline followed by an indent
  

  # Whitespace wrapper
  def ws(default_output) :
    return WS(default_output, slash_continuation=True, indent_continuation=True)

  # A lens that stores something between two lenses.
  def Between(lens_1, lens_2, label=None):
    return lens_1 + Until(lens_2, store=True, label=label) + lens_2

  keyword_chars = alphanums + "-"
  
  # Shortcut lens generators.
  with_label = lambda label: Word(keyword_chars, store=True, label=label)
  label = Word(keyword_chars, store=True, is_label=True)
  
  version_part = Between("(" + ws(""), ws("") + ")", "version")
  arch_part = Between("[", "]", "arch")
  package = label + ZM(ws(" ") + (version_part | arch_part))
  alternative_packages = G(List(G(package), ws(" ") + "|" + ws(" ")))
  lens = label + ws("") + ":" + ws(" ") + List(alternative_packages, "," + ws("\n  "))
  
  d("GET")
  concrete_reader = ConcreteInputReader(INPUT)
  token = lens.get(INPUT)
  d(token)

  # Do some spot checks
  d(token[0])
  assert token[0]["debhelper"]["version"] == ">= 7.0.0"
  assert token[5]["someotherapp"]["version"] == "> 1.2"
  assert token[7]["liblog-log4perl-perl"]["arch"] == "i386"


  d("PUT")
  concrete_reader.reset()
  for cr in [concrete_reader, None] :
    output = lens.put(token, cr)
    if cr :
      assert output == INPUT
    d(output)
    # TODO: Verify output

  # Change some things
  del token.dict[None][5]
  output = lens.put(token, INPUT)
  d(output)
  # TODO: Verify output
  
  """
    What can we say about the general structure of the file:
      - keywords -> Source, Build-Depends-Indep, libconfig-tiny-perl, ...
      - spaces -> indent, space that may contain line continuation
      - specific things -> email address, name with spaces, email, package version etc. details, urls
      - field content is continued on new line if indented.

    Would be nice:
    ws = <define whitespace>
    context = Context(keyword=Word(alphanums+"-"), whitespace=ws)
    package = Group(Label + Optional("("+Store("version")+")"))
    package_options = List(package, "|")
    depends_field = label + ":" + List(package_options, ",") + NL
  """


def touching_lens_test() :
  """Tests that touching lenses are correctly computed from the lens tree."""
  literal_d = Literal("D")
  and_1 = Literal("A") + Literal("B") + Literal("C")
  and_2 = literal_d + Literal("E") + Literal("F")
  and_3 = Literal("G") + OneOrMore(Literal("H")) + Literal("I")
  and_4 = Word(nums) + Literal("K") + Literal("L")
  lens = (and_1 | and_2) + (and_3 | and_4)
  
  # So we expect:
  #  A -> B -> C -> [G,J]  then   G -> H -> I -> None
  #  D -> E -> F -> [G,J]   ..    J -> K -> L -> None
  #  Also, due to OneOrMore, H -> H -> H ....

  # Let's follow the lenses and see.
  lens = literal_d
  assert isinstance(lens, Literal) and lens.literal_string == "D"
  lens = lens._get_next_lenses()[0]
  assert isinstance(lens, Literal) and lens.literal_string == "E"
  lens = lens._get_next_lenses()[0]
  assert isinstance(lens, Literal) and lens.literal_string == "F"
  lens = lens._get_next_lenses()[0]
  assert isinstance(lens, Literal) and lens.literal_string == "G"
  lens = lens._get_next_lenses()[0]
  assert isinstance(lens, Literal) and lens.literal_string == "H"
  h_lens = lens
  # Follow the loop of the H lens
  lens = lens._get_next_lenses()[0]
  assert isinstance(lens, Literal) and lens.literal_string == "H"
  lens = lens._get_next_lenses()[0]
  assert isinstance(lens, Literal) and lens.literal_string == "H"
  # Break the loop
  lens = h_lens._get_next_lenses()[1]
  assert isinstance(lens, Literal) and lens.literal_string == "I"
  # Now check we are at the end of a chain
  assert lens._get_next_lenses() == []

  # TODO: Dare we try with Recurse lens!!!



def apache_test() :
 
  # This will be a milestone.

  INPUT = """<VirtualHost *:80>
	ServerName wikidbasedemo.nickblundell.org.uk
  ServerAlias sb2.nickblundell.org.uk
	<Location />
    SetHandler python-program
    PythonHandler django.core.handlers.modpython
    PythonDebug On
    PythonAutoReload On
    #PythonPath "['/home/server/websites/django/wikidbasedemos'] + sys.path"
    #SetEnv DJANGO_SETTINGS_MODULE wbdemo
    PythonPath "['/home/server/websites/wikidbases/wbdemo1'] + sys.path"
    SetEnv DJANGO_SETTINGS_MODULE settings
	</Location>
  
  #Alias /admin_media "/usr/lib/python2.4/site-packages/Django-0.95-py2.4.egg/django/contrib/admin/media"
  Alias /admin_media "/usr/lib/python2.5/site-packages/django/contrib/admin/media"
  <Location "/admin_media/">
  SetHandler None
  </Location>
  
  Alias /media "/home/blundeln/working/wikidbase/wikidbase/media"
  <Location "/media/">
  SetHandler None
  </Location>

</VirtualHost>"""

  keyword_chars = alphas
  section = "<" + Word(keyword_chars, is_label=True) + Until(">", label="args") + ">"

def iface_test() :
  """Put the module through its paces."""
  
  INPUT = """iface  eth0 inet static
  address 67.207.128.159 # A comment
  netmask \\
     255.255.255.0
  gateway 67.207.128.1
  dns-nameservers 67.207.128.4 67.207.128.5
auto lo
# A comment
iface eth1 inet dhcp
auto eth1 eth2
"""

  # We want:
   # Interfaces
    # Interface
     # family
     # method
     # dns
     # gateway
    # autos = [[x, y], z]

  keyword_chars = alphanums+"-"
  with_label = lambda label: Word(keyword_chars, store=True, label=label)
  label = Word(keyword_chars, store=True, is_label=True)
  ws = WS(" ", slash_continuation=True)
  indent = Word(" \t", store=False, default="  ")
  comment = "#" + Until(WS("") + NewLine(), store=False)+ WS("") + NewLine()
  nl = WS("") + (NewLine() | comment) # Can end a line with a comment.
  
  class Interface(object):
    __lens__ = "iface" + ws + label + ws + with_label("address_family") + ws + with_label("method") + nl\
    + ZM(indent + G(label + ws + Until(nl, store=True), type=auto_list)+nl)

  interface = get(Interface, INPUT, check_fully_consumed=False)
  d(interface.__dict__)

  assert interface.address_family == "inet"
  assert interface.address == "67.207.128.159"

  interface.address_family = "fam"
  interface.gateway = "127.0.0.1"

  output = put(interface, INPUT, label="wlan2")
  d(output)
  output = create(interface, label="wlan2")
  d(output)
  # TODO: Verify outputs. 
  return

  auto = "auto" + ws + Until(nl, store=True, label="auto") + nl
  lens = ZM(G(iface)|auto|comment)

  """ Would be nice to write this like this:
    comment = "#" + Until() + NL   # Would be nice if lenses knew which other leaf lenses they touched.
    iface = Group("iface" + Label() + Store("family") + Store("method") + NL \ # Using default keyword matching
      + ZeroOrMore(indent + Group(Label() + Until() + NL)))
    auto = "auto" + Until() + NL

    lens = ZeroOrMore(iface|auto|comment)
  """

  # Give the lenses names based on their variable names.
  auto_name_lenses(locals())
  
  concrete_reader = ConcreteInputReader(INPUT)
  token = lens.get(concrete_reader)
  assert(concrete_reader.is_fully_consumed())
  d(token)
  return

  for mode in ["PUT", "CREATE"] :
    d("\n%s" % mode)
    atc = token.value
    atr = AbstractTokenReader(atc)
    if mode == "PUT" :
      concrete_reader.reset()
      output = lens.put(atr, concrete_reader)
    else :
      output = lens.create(atr)
    assert(atr.is_fully_consumed())
    d(output)
  return
  assert_match(output, """iface eth1 inet dhcp 
iface eth0 inet static 
  dns-nameservers 67.207.128.4 67.207.128.5 
  gateway 67.207.128.1 
  netmask 255.255.255.0 
  address 67.207.128.159 
auto lo 
auto eth1 eth2
""")


