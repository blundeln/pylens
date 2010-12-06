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
# Author: Nick Blundell <blundeln@gmail.com>
# Organisation: www.nickblundell.org.uk
#
from pylens import *
import pprint

from nbdebug import d

def main():

  INPUT_STRING = """iface eth0 inet static
  address 67.207.128.159
  netmask 255.255.255.0
  gateway 67.207.128.1
  dns-nameservers 67.207.128.4 67.207.128.5
auto lo
# A comment
iface eth1 inet dhcp

"""

  ws = OneOrMore(AnyOf(" \t", default=" "), default=" ")
  nl = Literal("\n")
  indent = nl + ws
  iface_param = ws + GroupLens(Word(alphanums + "-") + OneOrMore(ws + Word(alphanums+"."))) + Optional(ws) + nl
  iface = Literal("iface") + ws + Word(alphanums) + ws + Word(alphanums) + ws + Word(alphanums) + Optional(ws) + nl \
            + Optional(GroupLens(OneOrMore(iface_param)))
  auto = Literal("auto") + ws + Word(alphanums) + Optional(ws) + nl
  #comment = Literal("#") + Word(alphabet-"\n") + nl

  blank = Literal("\n")
  grammar = ZeroOrMore(iface|auto|blank)

  concrete_input_reader = ConcreteInputReader(INPUT_STRING)

  print("Beginning parsing of '%s'" % INPUT_STRING)

  abstract_token = grammar.lens_get(concrete_input_reader)

  print("abstract_token '%s'" % abstract_token)
  return
  
  abstract_token[3][1][0] = "monkey"
  del abstract_token[3][3][1]

  print("Modified abstract_token '%s'" % abstract_token)
  #return

  # Now, reset the input reader and put back.
  concrete_input_reader.reset()
  # XXX: Don't put in a list if flattening lists.
  output = grammar.lens_put(AbstractTokenReader(abstract_token), concrete_input_reader)

  print("unparsed: %s" % output)

  return
  print("\n\nCREATE\n\n")

  output = grammar.lens_create(AbstractTokenReader(["wlan", "chips", "peas"]))

  print("created: %s" % output)

def main2() :

  d("STARTED")

  INPUT_STRING = "NickBlundell,chips,MONKEY,sausages,nachos"
  INPUT_STRING = "NickBlundell"

  #grammar = Word(alphas) + ZeroOrMore(Literal(",") + OrLens(Word(alphas), Literal("MONKEY")))
  grammar = Word(alphas) + ZeroOrMore(Literal(",") + (Word(alphas) | Literal("MONKEY")))
  concrete_input_reader = ConcreteInputReader(INPUT_STRING)

  print("Beginning parsing of '%s'" % INPUT_STRING)

  abstract_token = grammar.lens_get(concrete_input_reader)

  print("abstract_token '%s'" % abstract_token)


  # Modify
  #abstract_token[0] = "Bert"
  #del abstract_token[1]
  #del abstract_token[1]
  #del abstract_token[1]
  #abstract_token.append("cheese")
  #abstract_token.append("mouse")
  #abstract_token.append("cat")
  
  #abstract_token = ["nothing", "tosee"]

  print("Modified abstract_token '%s'" % abstract_token)

  d("Remainder: '%s'" % concrete_input_reader.get_remaining())
  assert(not concrete_input_reader.get_remaining())

  d("\n\nPUTTING %s\n\n" % abstract_token)

  # Now, reset the input reader and put back.
  concrete_input_reader.reset()
  # XXX: Don't put in a list if flattening lists.
  output = grammar.lens_put(AbstractTokenReader(abstract_token), concrete_input_reader)

  print("unparsed: %s" % output)

  # TODO: Should also asset abstract reader is consumed fully.
  assert(not concrete_input_reader.get_remaining())
  d("Remainder: '%s'" % concrete_input_reader.get_remaining())




def main1() :
  
  INPUT_STRING = "hello"
  INPUT_STRING = "hello,Nick,MONKEY,Monkey"

  d("started")

  def word(char_set, lens_mode) :
    return CombineChars(OneOrMore(AnyOf(alphas, lens_mode=lens_mode)), lens_mode=lens_mode)
    

  grammar = Literal("hello") + Optional(OneOrMore(Literal(",") + word(alphas, lens_mode=Lens.STORE)))
  grammar = Literal("hello") + OneOrMore(Literal(",") + word(alphas, lens_mode=Lens.STORE))
  #grammar = Literal("hello") + Literal(",") + word(alphas, lens_mode=Lens.STORE) + Literal(",") + word(alphas, lens_mode=Lens.STORE) + Literal(",") + word(alphas, lens_mode=Lens.STORE)

  concrete_input_reader = ConcreteInputReader(INPUT_STRING)

  abstract_token = grammar.lens_get(concrete_input_reader)

  d(abstract_token)
  # Now modify
  abstract_token[0].append(["Orange"])

  
  d(abstract_token)

  assert(not concrete_input_reader.get_remaining())
  d("Remainder: '%s'" % concrete_input_reader.get_remaining())
  
  # Now, reset the input reader and put back.
  concrete_input_reader.reset()
  output = grammar.lens_put(AbstractTokenReader([abstract_token]), concrete_input_reader)

  d("unparsed: %s" % output)

  assert(not concrete_input_reader.get_remaining())
  d("Remainder: '%s'" % concrete_input_reader.get_remaining())


def main2() :
  
  d("started")

  s = ZeroOrMore(AnyOf("\t ", default=" "))

  class Variable(ParseObject):
    lens = Store(Word(alpha), "name") + (Literal("=") | Literal("|")) + Store(Word(alpha), "value", store_multiple=True) + ZeroOrMore(Literal(",") + Store(Word(alpha), "value", store_multiple=True)) + Literal("\n")

    def __init__(self, name=None, value=None) :
      self.name, self.value = name, value
    
    def __str__(self) :
      attr = self.__dict__
      return "%s: %s (tokens: '%s')" % (self.__class__.__name__, attr, self.parsed_token)

  class Container(ParseObject) :
    lens = Store(OneOrMore(Variable), "variables")

    def __str__(self) :
      return "%s: %s (tokens: '%s')" % (self.__class__.__name__, self.variables, self.parsed_token)
  
  input = """aa=bb
xx|yy,aa,yy
pp=qq
"""

  my_object = Container.parse(input)

  d(my_object)
  #return

  d("PARSED: -> >>%s<<\n\n\n" % my_object)
  new_object = Variable("new", ["variableA", "variableB", "variableC"])
  #d(new_object._unparse())
  #return
  
  # Modify it.
  #my_object.variables[1].name = "cheese"
  #my_object.variables.append(new_object)
  #my_object.variables[1:1] = [new_object]
  
  output = my_object._unparse()
  
  d("UNPARSED: -> >>%s<<" % output)



def main1() :
  d("started")

  SAMPLE_TEXT = """

 varB = valB
varC | valC
varD=valD
varE | valE

"""

  # TODO: Word consumes whitespace.
  s = Optional(Combine(ZeroOrMore(AnyOf("\t "))), default=" ")
  blanks = Optional(Combine(ZeroOrMore(AnyOf("\n \t"))))
  
  class Variable(ParseObject):
    lens = Store(Word(alpha), "name") + s + (Literal("=") | Literal("|")) + s + Store(Word(alpha), "value") + s + Literal("\n") 
    
    def __init__(self, name=None, value=None) :
      self.name, self.value = name, value

    def __repr__(self) :
      return "%s: %s -> %s" % (self.__class__.__name__, self.name, self.value)

  """
  my_variable = Variable.match("something = somethingval\n")

  d(my_variable)

  output = Variable.unparse(my_variable)
  d("Unparsed -> %s" % output)
  """
  
  class Container(ParseObject) :
    lens = blanks + Store(ZeroOrMore(Variable), "variables") + blanks
    variables = None
    
    def __str__(self) :
      return "%s: tokens %s, variables %s" % (self.__class__.__name__, self.parsed_token, self.variables)


  input = SAMPLE_TEXT

  my_container = Container.parse(input)
  d(my_container)
  # Alter it
  my_container.variables[2].value = "chickens"
  my_container.variables[1].name = "cheese"
  my_container.variables[2:2] = [Variable("nick", "nock")]

  d(my_container.variables)
  # Now unparse it
  print("\n\nUNPARSING\n\n")
  #output = my_container._unparse()
  output = Container.unparse(TokenReader([my_container]))


  d(output)


if __name__ == "__main__" :
  main()
