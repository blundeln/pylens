#
# Copyright (C) 2010 Nick Blundell.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# 
# The GNU GPL is contained in /usr/doc/copyright/GPL on a Debian
# system and in the file COPYING in the Linux kernel source.
# 
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
#

from pylens import *

from nbdebug import d


#
# Define our object lens model.
#

class Field(ParseObject):
  #eol = Optional(Literal("\n"), default="\n")
  #end_of_field = eol
  ws = Combine(ZeroOrMore(AnyOf("\t ")))
  line_join = Literal("\n") + OneOrMore(AnyOf("\t "))
  field_label = Store(Word(alphas), "name") + ws + Literal(":") 
  list_item =  Combine(AnyOf(alphanums) + OneOrMore(AnyOf(alphanums + "<>.@ ")))
  field_body = list_item + ws + ZeroOrMore(Literal(",") + ws + Optional(line_join) + list_item)
  lens = field_label + ws + field_body + Literal("\n")

class Container(ParseObject) :
  lens = Store(ZeroOrMore(Field) + ZeroOrMore(Literal("\n")), "fields")

  def __str__(self) :
    attrs = {"fields": self.fields}
    return "%s: %s (tokens: '%s')" % (self.__class__.__name__, attrs, self.parsed_token)
    

def main() :
  d("Started")

  input_string = open("../../resources/sample_config_files/debctrl.cfg","r").read()

  input_string = "Priority:  Peas \tn"

  input_string = """Uploaders: Dominique Dumont <dominique.dumont@xx.yyy>,
 gregor herrmann <gregoa@xxx.yy>,
 nick blundell <nick@email.com>
Uploaders: Dominique Dumont <dominique.dumont@xx.yyy>,
 gregor herrmann <gregoa@xxx.yy>

"""

  d(input_string)
  ob = Container.parse(input_string)

  d(ob)

  ##return

  # Modify
  ob.fields[0][0].name = "cheese"


  d("\n\nUNPARSING\n\n")

  d(ob._unparse())

  return
if __name__ == "__main__" :
  main()
