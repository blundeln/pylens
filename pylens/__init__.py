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
import inspect
from nbdebug import d, breakpoint, set_indent_function, IN_DEBUG_MODE
from excepts import *
from util import *
from token_collections import *
from readers import *



#########################################################
# Essential classes
#

# XXX: Not used yet.
class Charset:
  """Used for representing allowed characters and for handling negative sets, combination and checking for overlaps."""
  def __init__(self, charset, negate=False) :
    self.charset, self.negate = set(charset), negate
  
  def combine(self, other_charset) :
    if not isinstance(other_charset, Charset) :
      other_charset = Charset(other_charset)

    # If negation is the same, union the sets.
    if self.negate == other_charset.negate :
      return Charset(self.charset.union(other_charset.charset), negate=self.negate)

    # Handle opposite signed sets, which will always yield a negative set.
    positive_charset = self.negate and other_charset or self
    negative_charset = self.negate and self or other_charset
    return Charset(negative_charset.charset - positive_charset.charset, negate = True)


  def overlap(self, other_charset) :
    """Check if Charsets may match same characters."""
    if not isinstance(other_charset, Charset) :
      other_charset = Charset(other_charset)

    # Check intersection.
    if self.negate == False and other_charset.negate == False:
      return self.charset & other_charset.charset
    
    # Two negatives will always overlap, since space is infinite.
    if self.negate and other_charset.negate :
      return True
    
    # Handle mixed sign - no overlap if positive charset is a subset of negative subset.
    positive_charset = self.negate and other_charset or self
    negative_charset = self.negate and self or other_charset
    return not positive_charset.charset.issubset(negative_charset.charset)

  def __str__(self) :
    return "%s [%s]" % (self.negate and "not in" or "in", truncate("".join(self.charset)))

  @staticmethod
  def TESTS() :
    
    a = Charset("abcd")
    n = Charset("123")
    assert(not a.overlap(n))
    assert(a.overlap(a.combine(n)))

    not_a = Charset("abcd", negate=True)
    not_n = Charset("123", negate=True)
    assert(not_a.overlap(not_n))
    assert(not not_a.overlap(a))
    assert(not a.overlap(not_a))
    assert(a.overlap(not_n))

    newline = Charset("\n")
    not_newline = Charset("\n", negate=True)
    assert(not newline.overlap(not_newline))

    temp = newline.combine(Charset("XYZ"))
    assert(temp.charset == set(("X","Y","Z","\n")))
    temp = newline.combine(Charset("XYZ", negate=True))
    assert(temp.charset == set(("X","Y","Z")) and temp.negate)


#########################################################
# Base Lenses
#


class BaseLens(object): # object, important to use new-style classes, for inheritance, etc.
  """
  Base lens, which should be extended by all lenses.
  """
  
  def __init__(self, type=None, name=None) :
    self.type = type
    self.name = name
    self._recurse_lens = None

    # For connecting lenses for ambiguity checks
    self._next_lenses = []
    self._previous_lenses = []
  
  def get(self, concrete_input, check_fully_consumed=True, postprocess_token=True) :
    """
    If a parent lens plans to store a token, then it will retain more information (specifically on the tokens label)
    if it postprocesses the token immediately prior to storing it.
    """
    # If input a string, wrap in a concrete reader
    if isinstance(concrete_input, str) :
      concrete_input_reader = ConcreteInputReader(concrete_input)
    else :
      concrete_input_reader = concrete_input
      # Disable this if we are not the are the outer-most parser, since it doesn't make sense.
      check_fully_consumed = False

    # Show what we are doing.
    d("%s GET: CR -> '%s'" % (self, str(concrete_input_reader)))
    
    # Now call get proper to consume the input and parse a token, whether a store or not.
    with reader_rollback(concrete_input_reader) :
      abstract_data = self._get(concrete_input_reader)

    # Return nothing if this lens is not a STORE lens.
    # If we have a combinator, we always return what it returns (e.g. an empty container, a token from a sub-lens.
    if isinstance(self, Lens) :
      if self.store :
        assert abstract_data != None, "Should have got something here from our lens."
      else :
        return None

    d("Sucessfully GOT: %s" % (isinstance(abstract_data, str) and escape_for_display(abstract_data) or abstract_data))

    if check_fully_consumed and not concrete_input_reader.is_fully_consumed() :
      raise Exception("Concrete string not fully consumed: remaining: %s" % concrete_input_reader.get_remaining())
    
    if postprocess_token :
      return self._postprocess_outgoing_token(abstract_data)
    else :
      return abstract_data


  def put(self, abstract_data, concrete_input=None, check_fully_consumed=True, label=None) :
    """
    We handle a lot of the complexity of reader rollback and labelled tokens here so that specific lenses
    do not need to worry about this stuff.
    Since some lenses may return contents and a key/label, label lets us specify this when putting a token directly.
    """
    # TODO: implement check_fully_consumed appropriately for concrete and abstract readers.

    # Decide if token or reader
    # If token, normalise it to include the label

    # If a combinator lens, pass to _put (which takes a token or reader)
    # Now assume standard lens
    # If not AR
       # Normalise token.
       # If not a store lens, raise exception - cannot put a token into non-store lens.
       # pass to Lens._put (which takes a token, never a reader)
    # Assume AR
    #  If non-store
    #    return non_store_value -> consumed string or default.
    #  Else 
    #    We must try several normalised tokens
  
    assert abstract_data != None, "Must have some kind of abstract data to PUT."
    
    # Decide if we have been passed a token or a reader
    if isinstance(abstract_data, AbstractTokenReader) :
      abstract_token_reader = abstract_data
      token = None
    else :
      abstract_token_reader = None
      # Set the token, making sure to normalise it if a token collection (especially, to include the specified label token)
      abstract_data = self._preprocess_incoming_token(abstract_data, label=label)
      token = abstract_data

    # Normalise the concrete input into a reader.
    if concrete_input :
      concrete_input_reader = isinstance(concrete_input, str) and ConcreteInputReader(concrete_input) or concrete_input
    else :
      concrete_input_reader = None
   

    # Display what we are doing.
    type_of_data = abstract_token_reader and "ATR" or "Token"
    if concrete_input_reader :
      d("%s PUT: State -> (%s: %s, CR: '%s')" % (self, type_of_data, str(abstract_data), str(concrete_input_reader)))
    else :
      d("%s CREATE: State -> (%s: %s)" % (self, type_of_data, str(abstract_data)))
   

    #
    # Easy case: if we are a combinator, pass straight through to PUT proper.
    #
    if isinstance(self, CombinatorLens) :
      with reader_rollback(abstract_data, concrete_input_reader) :
        output = self._put(abstract_data, concrete_input_reader)
        d("Sucessfully %s: %s" % (concrete_input_reader and "PUT" or "CREATED", escape_for_display(output)))
        return output


    #
    # Now we can assume the case of a standard lens.
    #

    #
    # First handle case where we have a single token to put.
    #
    if token != None :
      # A non-store lens is not allowed to be passed a token to put. 
      if not self.store:
        raise LensException("Not a store lens: cannot put a token.")
      
      # Put the token
      with reader_rollback(concrete_input_reader) :
        output = self._put(token, concrete_input_reader)
        d("Sucessfully %s: %s" % (concrete_input_reader and "PUT" or "CREATED", escape_for_display(output)))
        return output

    #
    # Now we assume we are working with a standard lens that has been passed an abstract_token_reader
    # 
    assert(abstract_token_reader)


    # If we are a non-store lens, we need to output either from consumed concrete, or the default if we are doing CREATE
    if not self.store :
      # If PUT ...
      if concrete_input_reader :
        # Get the concrete text that this lens consumes with get, by remembering the initial state.
        start_position = concrete_input_reader.get_position_state()
        self.get(concrete_input_reader) # Note, get() handles rollback for us.
        output = concrete_input_reader.get_consumed_string(start_position)
      # If CREATE ...
      else :
        if self.default == None :
          # Note, if we used a plain Exception here, then an Or lens, say, could fail if not all lenses had a default.
          raise LensException("A default value must be set on this lens: %s." % (self))
        output = self.default
        
      d("Sucessfully %s: %s" % (concrete_input_reader and "PUT" or "CREATED", escape_for_display(output)))
      return output
   
    #
    # Now we assume we are a store lens and that we need potentially to try to put one of several next-tokens from the reader
    # due to possibility of having labelled tokens. 
    #
    
    #
    # Find a suitable set of candidate token labels.
    #
    if self.is_label : # If our lens is itself a label, we want the collection's label token
      candidate_labels = [AbstractTokenReader.LABEL_TOKEN]
    elif self.label :  # If our lens has a label with which to store a token, use this to retrieve the token.
      candidate_labels = [self.label]
    # If PUT, we want to find out if the concrete input generates a label (by running get), so we can put
    # things back where we found them when we have an is_label lens within the concrete structure.
    elif concrete_input_reader :
      # Must roll this back once we have found the label, so we can shortly call put (which again calls get())
      start_position = concrete_input_reader.get_position_state()
      original_token = self.get(concrete_input_reader) # get() will rollback if failed
      concrete_input_reader.set_position_state(start_position)
      #if hasattr(original_token, "label") : # Will only have a key if a GenericCollection
        #candidate_labels = [original_token.label]
      if isinstance(original_token, GenericCollection) :
        candidate_labels = [original_token.get_label_token()]
      else:
        candidate_labels = [None]
    # If CREATE, we have more flexibilty in which token we put, and we can soon have a tie-breaker
    # to decide which to actually go with.
    else :
      # Candidates are any label (including None) in the abstract reader, excluding the LABEL_TOKEN.
      candidate_labels = abstract_token_reader.position_state.keys()
      if AbstractTokenReader.LABEL_TOKEN in candidate_labels :
        candidate_labels.remove(AbstractTokenReader.LABEL_TOKEN)

    d("candidate labels %s" % candidate_labels)

    #
    # Now try to put tokens with these labels, and go with the most suitable put.
    #

    # Remember the readers state, before we start trying to put tokens, since we'll not commit until we've tried
    # all the candidate tokens.
    start_reader_state = get_readers_state(abstract_token_reader, concrete_input_reader)
    best_output = None   # Will be a tuple -> (output, end_state)

    #
    # TODO: Since now non-store lenses are not considered here, it doesn't matter
    # which lens, since all use a token, so just down to preference.
    #

    for candidate_label in candidate_labels :
      # Try to get the token from the token reader - fail (e.g. if not more tokens) -> continue, try next label
      d("Trying candidate label '%s'" % candidate_label)
      try :
        candidate_token = abstract_token_reader.get_next_token(label=candidate_label)
      except LensException:
        continue
     
      # Normalise the token and set/update its label token to that which now points at it, if a GenericCollection
      # XXX: Note the label token may not be consumed by the lens, so we should ignore non-consumption of the label for now.
      # XXX: Hmm: But if this lens does not use label, does that mean it should be an is_label... need to think about this.
      # TODO: Might as well use put rather than _put, so normalisation done
      # there
      candidate_token = self._preprocess_incoming_token(candidate_token, label=candidate_label)

      # Try to put the token - fail -> rollback, continue
      try :
        output = self._put(candidate_token, concrete_input_reader)
        if not best_output or len(output) > best_output[0] :
          best_output = (output, get_readers_state(abstract_token_reader, concrete_input_reader))
      except LensException:
        # Failed to put token, so restore the initial readers state, ready to try another candidate label.
        continue
      
      # Then restore the initial state, for the next PUT attempt.
      set_readers_state(start_reader_state, abstract_token_reader, concrete_input_reader)

    # Choose the best output and use the state it left us in.
    if best_output :
      set_readers_state(best_output[1], abstract_token_reader, concrete_input_reader)
      output = best_output[0]
      d("Sucessfully %s: %s" % (concrete_input_reader and "PUT" or "CREATED", escape_for_display(output)))
      return output
    
    # If we have no sucessful put, raise exception - this will happen when all tokens have been consumed.
    raise LensException("%s store lens %s failed to put a token." % (concrete_input_reader and "PUT" or "CREATE", self))


  
  def create(self, abstract_data, label=None, check_fully_consumed=True) :
    return self.put(abstract_data, None, label=label, check_fully_consumed=check_fully_consumed)


  #-------------------------
  # For overriding
  #
  
  def _get(self, concrete_input_reader) :
    raise NotImplementedError("in class %s" % self.__class__)

  def _put(self, abstract_data, concrete_input_reader) :
    raise NotImplementedError("in class %s" % self.__class__)
  

  #-------------------------
  # Private
  #

  def _create_collection(self) :
    """Creates a new collection for storing tokens based on this lens' type."""
    collection_class = TokenTypeFactory.get_collection_class(self.type)
    return collection_class()

  def _get_label_of_token(self, token, origin_lens) :
    """Gets the label by which to store the specified token, which can come from the token itself or from the lens."""
    # If this token has a token label, use that, else check if the lens has a token.
    label = None
    if isinstance(token, AbstractCollection) :
      label = token.get_label_token()
    if not label and isinstance(origin_lens, Lens) :
      label = origin_lens.label

    return label
  
  #
  # Pre- and post-processing functions to ensure internally tokens are strings or AbstractCollections,
  # whilst allowuing the user to use other types (e.g. int, float, list, dict, classes).
  #

  def _preprocess_incoming_token(self, token, label=None) :
    """Normalise the token before it is PUT by the lens."""
    token = TokenTypeFactory.normalise_incoming_token(token, self.type)
    
    # Roll the label into a AbstractCollection, for lenses that parse labels to be able to PUT back.
    if label and isinstance(token, AbstractCollection) :
      token.set_label_token(label, overwrite=True) # If label exists from GET token, overwrite it.
    
    return token


  def _postprocess_outgoing_token(self, abstract_data) :
    """If this lens has an explicit type, try to coerce the abstract_data into that type."""
    # Note that the data may be a single value or some collection of values.
    return TokenTypeFactory.cast_outgoing_token(abstract_data, self.type) 


  def _preprocess_lens(self, lens) :
    """Preprocesses a lens to ensure any type to lens conversion and checking for recursive lens."""
    lens = coerce_to_lens(lens)

    d(str(lens))

    recurse_lens = isinstance(lens, Recurse) and lens or lens._recurse_lens
    if recurse_lens :
      recurse_lens.bind_lens(self)
      self._recurse_lens = recurse_lens
    
    return lens

  #-------------------------
  # For ambiguity checking.
  #

  """These allow us to compute lenses that touch in the tree by returning the possible first leaf lenses under this lens."""
  def get_first_lenses(self):
    raise NotImplementedError("in class %s" % self.__class__)
  def get_last_lenses(self):
    raise NotImplementedError("in class %s" % self.__class__)

  def _connect_to(self, other_lens) :
    # Note, ignore duplicate, which can be cause by flattening Ands
    if other_lens not in self._next_lenses :
      d("Linking %s to %s" % (self, other_lens))
      self._next_lenses.append(other_lens)
      assert self not in other_lens._previous_lenses
      other_lens._previous_lenses.append(self)

  def _get_next_lenses(self) :
    """Gets the set of possible next leaf lenses (i.e. the lenses that touch this lens)"""
    return self._next_lenses
  def _get_previous_lenses(self) :
    """Gets the set of possible previous leaf lenses (i.e. the lenses that touch this lens)"""
    return self._previous_lenses

  #-------------------------
  # operator overloads
  #
  
  def __add__(self, other_lens): return And(self, self._preprocess_lens(other_lens))
  def __or__(self, other_lens): return Or(self, self._preprocess_lens(other_lens))

  # Reflected operators, so we can write: lens = "a string" + <some_lens>
  def __radd__(self, other_lens): return And(self._preprocess_lens(other_lens), self)
  def __ror__(self, other_lens): return Or(self._preprocess_lens(other_lens), self)
  

  
  #-------------------------
  # For debugging
  #
  
  def _display_id(self) :
    """Useful for identifying specific lenses when debugging."""
    if self.name :
      return self.name
    return str(hash(self) % 256)  # Hash gives us a reasonably easy to distinguish id for lens if no name set.

  def __str__(self) :
    return "%s(%s)" % (self.__class__.__name__, self._display_id())
  __repr__ = __str__


def coerce_to_lens(lens_operand):
  """Intelligently convert a type to a lens (e.g. string instance to a Literal lens)"""
  if isinstance(lens_operand, str) :
    lens_operand = Literal(lens_operand)
  elif inspect.isclass(lens_operand) and hasattr(lens_operand, "__lens__") :   
    lens_operand = Group(lens_operand.__lens__, type=lens_operand)
  
  assert isinstance(lens_operand, BaseLens), "Unable to coerce %s to a lens" % lens_operand
  return lens_operand

class Lens(BaseLens) :
  """Base class of standard lenses, that can get and store an abstract token."""
  def __init__(self, store=False, label=None, is_label=False, default=None, name=None, **kargs) :
    super(Lens, self).__init__(**kargs)
    self.store    = store     # Controls whether or not this lens returns or consumes a token in GET, PUT respectively.
    self.label    = label     # Allows this lens to use a labelled token, for storage and retrival.
    self.is_label = is_label  # If set, this lens' token will be used as a label for the current container.
    self.default  = default   # Default output for CREATE should this lens be acting as a non-store lens.
    self.name     = name      # Specific name for this lens - useful only for debugging.

    # if the lens is or has a label, implies it is a store lens.
    if self.is_label or self.label:
      self.store=True

  def _put(self, abstract_token, concrete_input_reader) :
    """Note that this lens expects to put an individual token, not a reader as with CombinatorLens"""
    raise NotImplementedError("in class %s" % self.__class__)


  def get_first_lenses(self):
    return [self]
  def get_last_lenses(self):
    return [self]

  #-------------------------
  # For debugging
  #
  
  def _display_id(self) :
    """Useful for identifying specific lenses when debugging."""
    return self.name or str(hash(self) % 256)  # Hash gives us a reasonably easy to distinguish id for lens if no name set.

class CombinatorLens(BaseLens) :
  """Base class of lenses that combine other lenses in some way."""
  
  def _put(self, abstract_data, concrete_input_reader) :
    """Note that this lens expects to be passed either an individual token or a reader."""
    raise NotImplementedError("in class %s" % self.__class__)

  def _store_token(self, token, lens, token_collection):
    """Stores the given token, generated by the given lens, appropriately (e.g. based on label, etc.) in the token collection."""
    if token == None :
      return
   
    # Scenarios
    #  - We are about to add a token to our current collection
    #  - The token may or may not be a collection itself
    #  - The lens may or may not be a CombinatorLens
    #  - Special case 1: If we have a combinator lens and this is a collection
    #    - merge it into the current collection (to avoid by default excessive nesting)
    #  - Special case 2: if a standard lens and has is_label set, store as label token
    #  - Otherwise, the token is going to be added with a label, which may be None:
    #     So we need to decide the label:
    #      - If GenericCollection, set label to key token or None
    #      - else, set to lens label

    d("Storing token %s" % token)

    # Useful variables
    is_combinator = isinstance(lens, CombinatorLens)
    is_token_collection = isinstance(token, AbstractCollection)
    
    # Check if this token (if a collection itself) should be merged (e.g. for nested Ands, OneOrMore, etc.)
    # Note that a CombinatorLens may not necessarily return a GenericCollection (e.g. Or)
    if is_combinator and is_token_collection :
      token_collection.merge(token)
      return
      
    # Handle the case where the token itself is a label for the current collection
    if not is_combinator and lens.is_label :
      token_collection.set_label_token(token)
      return

    # Now look to see if the token has a label by which to store it.
    label = self._get_label_of_token(token, lens)

    # Now add the label to the collection - postprocessing the token, to make it easier for user manipulation.
    token_collection.add_token(lens._postprocess_outgoing_token(token), label)


##################################################
# Core lenses
#

    
class And(CombinatorLens) :

  def __init__(self, left_lens, right_lens, **kargs):
   
    super(And, self).__init__(**kargs)
    self.lenses = []

    # Preprocess lenses
    left_lens = self._preprocess_lens(left_lens)
    right_lens = self._preprocess_lens(right_lens)

    # Flatten sub-lenses that are also Ands, so we don't have too much nesting, which makes debugging lenses a nightmare.
    for lens in [left_lens, right_lens] :
      if isinstance(lens, self.__class__) : 
        self.lenses.extend(lens.lenses)
      else :
        self.lenses.append(lens)

    # Link the edge lenses.
    for i in range(len(self.lenses)-1) :
      lens = self.lenses[i]
      next_lens = self.lenses[i+1]
      for last_lens in lens.get_last_lenses() :
        for first_lens in next_lens.get_first_lenses() :
          assert first_lens != last_lens, "Should never happen!"
          last_lens._connect_to(first_lens)


  def _get(self, concrete_input_reader) :
    token_collection = self._create_collection()
    for lens in self.lenses :
      self._store_token(lens.get(concrete_input_reader, postprocess_token=False), lens, token_collection)
    return token_collection


  def _put(self, abstract_data, concrete_input_reader) :
    
    # And can accept the current abstract reader, since nested Ands are avoided in lens construction.
    if isinstance(abstract_data, AbstractTokenReader) :
      abstract_token_reader = abstract_data
    elif isinstance(abstract_data, AbstractCollection) :
      abstract_token_reader = AbstractTokenReader(abstract_data)
    else :
      raise LensException("Expected a collection token.")

    output = ""
    for lens in self.lenses :
      output += lens.put(abstract_token_reader, concrete_input_reader)

    return output


  def get_first_lenses(self):
    return self.lenses[0].get_first_lenses()

  def get_last_lenses(self):
    return self.lenses[-1].get_last_lenses()


  @staticmethod
  def TESTS() :
    # GET
    lens = AnyOf(alphas, store=True) + AnyOf(nums, store=True, label="2nd_char") + AnyOf(alphas, store=True, is_label=True) + AnyOf(nums, store=True)
    token = lens.get("m1x3p6", check_fully_consumed=False)
    assert_match(str(token), "...<x> -> {None: ['m', '3'], '2nd_char': ['1']}")
    # PUT
    d("PUT")
    tokens = GenericCollection(["n", "8"])
    tokens["2nd_char"] = "4"
    output = lens.put(tokens, "p2w3z5", check_fully_consumed=False, label="g")
    d(output)
    assert output == "n4g8"

    # CREATE
    output = lens.create(tokens)
    assert output == "n4g8"
    
    d("TEST TYPE CASTING")
    lens = And(AnyOf(alphas, store=True) + AnyOf(nums, store=True, type=int), AnyOf(alphas, store=True), type=list)
    assert lens.get("m1x") == ["m", 1, "x"]
    assert lens.put(["n", 4, "d"], "m1x") == "n4d"
    

class Or(CombinatorLens) :
  """In the GET direction, the longest match is returned; in the PUT direction the left-most token-consuming token is favoured else left-most lens."""
  
  def __init__(self, left_lens, right_lens, **kargs):
    super(Or, self).__init__(**kargs)
    self.lenses = []
    # TODO: Put lenses attrib in CombinatorLens along with preprocessing.
    # Preprocess lenses
    left_lens = self._preprocess_lens(left_lens)
    right_lens = self._preprocess_lens(right_lens)

    # Flatten sub-lenses that are also Ors, so we don't have too much nesting, which makes debugging lenses a nightmare.
    for lens in [left_lens, right_lens] :
      if isinstance(lens, self.__class__) :
        self.lenses.extend(lens.lenses)
      else :
        self.lenses.append(lens)


  def _display_id(self) :
    return " | ".join([str(lens) for lens in self.lenses])

  def _get(self, concrete_input_reader) :
  
    # Scenarios
    #  - More than one lens may match
    #    - Consider AnyOf(alpha) | Empty() -> Empty() will always match
    #    - So test all and return longest match (i.e. progresses the concrete input the furthest) if several match
    #    - If matches are same length, return firstmost match.
    #  - Note that we must be careful to differentiate between failing to get a token and getting a None token (e.g from Empty())
    # - Perhaps could toggle greedy/non-greedy (i.e. order priority) GET per Or() instance.
    # TODO: Could also get longest consumption that gives a token firstmost.

    # Remember the starting state (position) of the concrete reader.
    concrete_start_state = concrete_input_reader.get_position_state()
    
    # Try all lenses and store token and end_state
    best_match = None
    for lens in self.lenses :
      # Ensure the reader is at the start state for each lens to parse afresh.
      concrete_input_reader.set_position_state(concrete_start_state)
      try :
        token = lens.get(concrete_input_reader)
        end_state = concrete_input_reader.get_position_state()
        # Check if this is the best match so far, favouring firstmost lenses if equal lengthed parse.
        if not best_match or end_state > best_match[1] :
          best_match = [token, end_state]
      except LensException:
        pass

    lens_assert(best_match != None, "Or should match at least one of the lenses")

    # Restore the end state of the best match and return the token.
    concrete_input_reader.set_position_state(best_match[1])
    return best_match[0]

  def _token_should_be_merged(self) :
    # E.g. if one of our sub-lenses is and And, OneOrMore, etc.
    return True

  def _put(self, abstract_data, concrete_input_reader) :
 
    # TODO: Should put longest, perhaps first-most more intuitive for lens designers, so they have some control.
    # Scenarios
    # We may be passed a Token or an AbstractTokenReader
    # PUT and CREATE:
    #  - Try to (straight) PUT all the lenses and use the firstmost sucess, favouring lenses that consume abstract tokens.
    #  - Do this first, since we prefer to weave things back into their concrete structure.
    # PUT
    #  - BUT, if all PUTs fail, try cross PUTting: get LL create RL, then GET RL CREATE LL - could put this with the CREATE -
    #    since we may have change the abstract from one token type to the other.
    
    if isinstance(abstract_data, AbstractTokenReader) :
      abstract_token_reader = abstract_data
    else :
      abstract_token_reader = None

    # Remember the starting state of the readers - note, this does nothing if readers are None.
    start_readers_state = get_readers_state(abstract_token_reader, concrete_input_reader)

    d("Trying straight put.")
    # Try all lenses and store reader and end_state of the longest PUT
    # This handles straight PUTs (vs. cross PUTs) and CREATE (when concrete_input_reader == None)
    best_PUT = None
    lens_consumed_tokens = False
    for lens in self.lenses :
      # For each lens, ensure the readers state is reset back to the start state.
      set_readers_state(start_readers_state, abstract_token_reader, concrete_input_reader)
      try :
        output = lens.put(abstract_data, concrete_input_reader)
        end_state = get_readers_state(abstract_token_reader, concrete_input_reader)
        
        # If we are dealing with an AbstractTokenReader, then check to see if the lens consumed any tokens.
        # otherwise, we assume that it did, since otherwise the PUT would fail before we got here.
        if abstract_token_reader :
          lens_consumed_tokens = start_readers_state[0] != end_state[0]
        else :
          lens_consumed_tokens = True

        # Update the best action.
        if not best_PUT or (lens_consumed_tokens and not best_PUT[2]) : # We prefer the first-most lens that consumes tokens.
          best_PUT = [output, end_state, lens_consumed_tokens]
          d("BEST straight put: %s" % best_PUT)
          if lens_consumed_tokens : break # We have what we want.
      except LensException:
        pass
      
    # If already we have a put that consumed a token, go with those results.
    if best_PUT and best_PUT[2]:
      set_readers_state(best_PUT[1], abstract_token_reader, concrete_input_reader)
      return best_PUT[0]

    # Handle cross PUTs, which get (consume) from one lens and create with another, which is not relevant for CREATE.
    if concrete_input_reader :
      d("Trying cross put.")
      for GET_lens in self.lenses:
        for CREATE_lens in self.lenses :
          if CREATE_lens == GET_lens :
            continue # Already tried straight PUTs
          
          # For each lens, ensure the readers state is reset back to the start state.
          set_readers_state(start_readers_state, abstract_token_reader, concrete_input_reader)
          try :
            GET_lens.get(concrete_input_reader) # Consume and discard with the GET lens.
            output = CREATE_lens.create(abstract_data)
            end_state = get_readers_state(abstract_token_reader, concrete_input_reader)
            
            # Again, when we have a reader, check if tokens were consumed, so that we might prioritise.
            if abstract_token_reader :
              lens_consumed_tokens = start_readers_state[0] != end_state[0]
            else :
              lens_consumed_tokens = True
            
            # Update the best action.
            if not best_PUT or (lens_consumed_tokens and not best_PUT[2]) : # We prefer the first-most lens that consumes tokens.
              best_PUT = [output, end_state, lens_consumed_tokens]
            
          except LensException:
            pass
          
          if lens_consumed_tokens : break # We have what we want.
        if lens_consumed_tokens : break # Break works only on immediate loop - one of the few justifications for a goto!

    # Now go with our best output.
    if best_PUT :
      set_readers_state(best_PUT[1], abstract_token_reader, concrete_input_reader)
      return best_PUT[0]

    lens_assert(False, "Or should PUT (or CREATE-GET) at least one of the lenses")
      
  def get_first_lenses(self):
    """Return list of possible first lenses."""
    first_lenses = []
    for lens in self.lenses :
      first_lenses.extend(lens.get_first_lenses())
    return first_lenses

  def get_last_lenses(self):
    """Return list of possible last lenses."""
    last_lenses = []
    for lens in self.lenses :
      last_lenses.extend(lens.get_last_lenses())
    return last_lenses


  @staticmethod
  def TESTS() :
    d("GET")
    store = True
    lens = AnyOf(nums, store=store, default="4") | AnyOf(alphas, store=store, default="B") | (AnyOf(alphanums, label="l", store=store, default="3") + AnyOf(alphas, store=store, default="x"))
    token = lens.get("2m_x3p6", check_fully_consumed=False)
    d(token)
    assert_match(str(token), "...['m'], 'l': ['2']...")
    
    d("PUT")
    token["l"] = '8'
    token[0] = 'p'
    output = lens.put(token, "2m_x3p6", check_fully_consumed=False)
    d(output)
    assert output == "8p"
    
    d("CREATE")
    token["l"] = '8'
    token[0] = 'p'
    output = lens.create(token, check_fully_consumed=False)
    d(output)
    assert output == "8p"
  
    
    # Now see what happens with a non-store lens.
    d("NON-STORE")
    store = False
    lens = AnyOf(nums, store=store) | AnyOf(alphas, store=store, default="B") | (AnyOf(alphanums, label="l", store=store, default="3") + AnyOf(alphas, store=store, default="x"))

    d("GET")
    token = lens.get("2m_x3p6", check_fully_consumed=False)
    # This should give us an empty GenericCollection
    assert isinstance(token, GenericCollection) and not token.dict

    d("PUT")
    output = lens.put(token, "2m_x3p6")
    assert output == "2m"
    d(output)
    
    d("CREATE")
    output = lens.create(token)  # Note that token is an empty GenericCollection
    d(output)
    # We expect '3x' (defaults with And's AnyOfs, since the AnyOf lenses reject being passed a token.
    assert output == "3x"
    
    output = lens.create(AbstractTokenReader(token))
    d(output)
    # We expect 'B', since reader does not force tokens on lens and the first AnyOf has no default, the next does,
    # which is 'B'
    assert output == "B"
    

class OneOrMore(CombinatorLens) :

  def __init__(self, lens, min_items=1, max_items=None, **kargs):
    
    super(OneOrMore, self).__init__(**kargs)
    self.lens = lens

    # Connect the lens to itself, since it may follow or preced itself.
    for last_lens in self.lens.get_last_lenses() :
      for first_lens in self.lens.get_first_lenses() :
        # Lens may connect to itself here (e.g. OM(Literal("A"))
        last_lens._connect_to(first_lens)



    # TODO: Make use if these bounds
    assert(min_items >= 1)
    self.min_items, self.max_items = min_items, max_items
  
  def _get(self, concrete_input_reader) :
    
    # TODO: Prepare appropriate type
    token_collection = self._create_collection()
    # Consume as many as possible until GET fails.
    #XXX: What if pass empty lens
    no_GOT = 0
    while True:
      try :
        self._store_token(self.lens.get(concrete_input_reader, postprocess_token=False), self.lens, token_collection)
        no_GOT += 1
      except LensException:
        break
    
    lens_assert(no_GOT > 0, "Must GET at least one.")
    return token_collection


  def _put(self, abstract_data, concrete_input_reader) :
    
    # TODO: Suppose the lens does not store tokens, we could create indefinitely.
    # So we can check if it consumes tokens.
    # Perhaps if we see that no tokens were consumed in a put, allow only one.

    # We can accept the current abstract reader or a GenericCollection.
    if isinstance(abstract_data, AbstractTokenReader) :
      abstract_token_reader = abstract_data
    elif isinstance(abstract_data, AbstractCollection) :
      abstract_token_reader = AbstractTokenReader(abstract_data)
    else :
      raise LensException("Expected an AbstractTokenReader or AbstractCollection")

    output = ""
    num_output = 0

    # Scenarios
    #  PUT:
    #   - PUT as many items as possible
    #   - CREATE remaining items, if any
    #   - GET (i.e. consume) any remaining items from input
    #  CREATE:
    #   - CREATE items, if any
    #  BUT:
    #   - Suppose the lens does not store tokens, we could create indefinitely.

    # Try to PUT some
    if concrete_input_reader :
      while True :
        try :
          output += self.lens.put(abstract_token_reader, concrete_input_reader)
          num_output += 1
        except LensException:
          break

    # Try to CREATE some.
    while True :
      try :
        start_state = abstract_token_reader.get_position_state()
        lens_output = self.lens.create(abstract_token_reader)
        end_state = abstract_token_reader.get_position_state()
        
        # If the lens consumed no tokens, be sure to avoid an infinite loop (e.g. if lens is an non-store lens)
        if end_state == start_state :
          # We will let one of these through to be consistend with OneOrMore definition: at least one.
          if num_output == 0 :
            output += lens_output
            num_output += 1
          break
        
        output += lens_output
        num_output += 1
      except LensException:
        break

    # Try to GET some - so if we now have fewer abstract tokens than were in concrete input.
    if concrete_input_reader :
      while True :
        try :
          self.lens.get(concrete_input_reader)
        except LensException:
          break

    lens_assert(num_output > 0, "Should process at least one item.") 

    return output

  def get_first_lenses(self):
    return self.lens.get_first_lenses()
  def get_last_lenses(self):
    return self.lens.get_last_lenses()

  @staticmethod
  def TESTS() :
    d("GET")
    lens = OneOrMore(AnyOf(alphanums, store=True))
    token = lens.get("m1x3_p6", check_fully_consumed=False)
    d(token)
    assert_match(str(token), "...['m', '1', 'x', '3']...")
    try : lens.get("_m1x3_p6", check_fully_consumed=False); assert False, "This should fail - we should not get here!"
    except: pass

    d("PUT")
    concrete_reader = ConcreteInputReader("m1x3_p6")
    output = lens.put(["r","o","b","0","t"], concrete_reader)
    d(output)
    assert concrete_reader.get_consumed_string(0) == "m1x3"
    assert output == "rob0t"
    
    concrete_reader = ConcreteInputReader("m1x3_p6")
    output = lens.put(["N", "B"], concrete_reader)
    assert concrete_reader.get_consumed_string(0) == "m1x3"
    assert output == "NB"

    d("CREATE")
    output = lens.create(["N", "B"])
    assert output == "NB"

    # Test for infinite create problem.
    lens = OneOrMore(AnyOf(alphanums, store=False, default="q"))
    output = lens.put([], "m1x3_p6")
    assert output == "m1x3" # Happy to put back what was there.
    output = lens.put([], "_p6")
    assert output == "q" # We at least want to create one, so use default.
    
    d("Type testing")
    lens = OneOrMore(AnyOf(alphanums, store=True), type=list)
    token = lens.get("m1x3_p6", check_fully_consumed=False)
    d(token)
    assert isinstance(token, list)
    output = lens.put(['x','y','z'], "m1x3_p6")
    d(output)

class Recurse(CombinatorLens):
  # During construction, lenses pass up references to Recurse so that it may bind to
  # the top level lens, though this must be frozen to the local lens definition.
  # TODO: Freeze ascention - will use reflection to freeze when find var to which this Recurse binds.
  # TODO: Reconcile different recurse lenses as the same lens (e.g. X + Recurse() + Z | Y + Recurse() + P)
  #       Only required if we allow multiple instances
  def __init__(self, **kargs):
    super(Recurse, self).__init__(**kargs)
    self._bound_lens = None
    return   
    # Lets find which lens we were initialised under.
    import inspect

    

    frame = inspect.currentframe()
    frame = frame.f_back
    d(frame.f_locals)
    return
    #d(frame.f_locals["self"])
    while frame: #"self" in frame.f_locals :
      if "self" in frame.f_locals :
        d(frame.f_locals)
      frame = frame.f_back
    """for i in range(0, callerLevel) :
        callerFrame = callerFrame.f_back
      location = getCallerLocation(callerFrame)
      message = indent + location+": " + message
  """
  
  def bind_lens(self, lens) :
    d("Binding to lens %s" % lens)
    self._bound_lens = lens
  
  def _get(self, concrete_input_reader) :
    assert self._bound_lens, "Recurse was unable to bind to a lens."
    return self._bound_lens._get(concrete_input_reader)

  def _put(self, abstract_data, concrete_input_reader) :
    assert self._bound_lens, "Recurse was unable to bind to a lens."
    return self._bound_lens._put(abstract_data, concrete_input_reader)
 
  # TODO: When Recurse binds, it could replace the links with touching lenses.
  # Or perhaps we override get_next_lenses - perhaps not a problem when it comes to getting char sets
  # since we will be bound by then.
  def get_first_lenses(self):
    return [self]
  def get_last_lenses(self):
    return [self]

  @staticmethod
  def TESTS() :
    lens = ("[" + (Recurse() | Word(alphas, store=True)) + "]")
    token = lens.get("[[hello]]")
    d(token)
    assert_match(str(token), "...['hello']...")
    output = lens.put(["monkey"], "[[hello]]")
    d(output)
    assert output == "[[monkey]]"

class AnyOf(Lens) :
  
  def __init__(self, valid_chars, negate=False, **kargs):
    super(AnyOf, self).__init__(**kargs)
    self.valid_chars, self.negate = valid_chars, negate
 
  def _get(self, concrete_input_reader) :
    
    char = None
    try:
      char = concrete_input_reader.get_next_char()
      if not self._is_valid_char(char) :
        raise LensException("Expected char %s but got '%s'" % (self._display_id(), truncate(char)))
    except EndOfStringException:
      raise LensException("Expected char %s but at end of string" % (self._display_id()))
    
    return char


  def _put(self, abstract_token, concrete_input_reader) :
    # If this is PUT (vs CREATE) then consume input.
    if concrete_input_reader :
      self.get(concrete_input_reader)
    lens_assert(isinstance(abstract_token, str) and len(abstract_token) == 1 and self._is_valid_char(abstract_token), "Invalid abstract_token '%s'." % abstract_token)
    return abstract_token


  def _is_valid_char(self, char) :
    if self.negate :
      return char not in self.valid_chars
    else :
      return char in self.valid_chars

  def _display_id(self) :
    if self.name :
      return self.name
    if self.negate :
      return "not in [%s]" % truncate(self.valid_chars)
    else :
      return "in [%s]" % truncate(self.valid_chars)
  

  @staticmethod
  def TESTS() :
    d("GET")
    lens = AnyOf(alphas, store=True)
    token = lens.get("monkey", check_fully_consumed=False)
    assert token == "m"

    d("PUT")
    output = lens.put("d", "monkey")
    d(output)
    assert output == "d"
    
    d("CREATE")
    output = lens.create("x")
    d(output)
    assert output == "x"

    d("TEST type coercion")
    lens = AnyOf(nums, store=True, type=int)
    assert lens.get("3") == 3
    assert lens.put(8, "3") == "8"

class Empty(Lens) :
  """Matches the empty string, used by Optional().  Can set modes for special empty matches."""
  
  # Useful modifiers
  START_OF_TEXT = "START_OF_TEXT"
  END_OF_TEXT   = "END_OF_TEXT"

  def __init__(self, mode=None, **kargs):
    super(Empty, self).__init__(**kargs)
    self.default = ""
    self.mode = mode

  def _get(self, concrete_input_reader) :
    
    if self.mode == self.START_OF_TEXT :
      lens_assert(concrete_input_reader.get_pos() == 0, "Not at start of text.")
    elif self.mode == self.END_OF_TEXT :
      lens_assert(concrete_input_reader.is_fully_consumed(), "Not at end of text.")

    return ""  # Note this is actually a token (not None) that could potentially be stored.

  def _put(self, abstract_token, concrete_input_reader) :
    lens_assert(isinstance(abstract_token, str) and abstract_token == "")
    return ""

  @staticmethod
  def TESTS() :
    
    
    # With store
    lens = Empty(store=True)
    assert lens.get("anything", check_fully_consumed=False) == ""
    assert lens.put("", "anything") == ""
    try :
      lens.put(" ", "anything"); assert False
    except LensException :
      pass # The token ' ' is invalid for this lens.
    assert lens.create("") == ""

    # Without store
    lens = Empty()
    assert lens.get("anything", check_fully_consumed=False) == None
    assert lens.put(AbstractTokenReader(GenericCollection()), "anything") == ""
    try :
      lens.put("", "anything"); assert False
    except LensException :
      pass # Even though token valid, this is not a store lens, so will fail.
    
    # Try special modes.
    lens = Empty(mode=Empty.START_OF_TEXT)
    concrete_reader = ConcreteInputReader("hello")
    concrete_reader.get_next_char()
    try : token = lens.get(concrete_reader); assert False, "This should fail - we should not get here!"
    except LensException: pass


class Group(Lens) :
  """A lens that wraps any lens as a standard lens, mainly useful for keeping tokens from CombinatorLenses grouped."""

  def __init__(self, lens, **kargs):
    # Little point in using a group if it is not to be stored, so automatically set it here.
    if "store" not in kargs :
      kargs["store"] = True
    super(Group, self).__init__(**kargs)
    self.lens = lens

  def _get(self, concrete_input_reader) :
    return self.lens.get(concrete_input_reader)

  def _put(self, abstract_token, concrete_input_reader) :
    return self.lens.put(abstract_token, concrete_input_reader)

  @staticmethod
  def TESTS() :
    
    d("GET")
    CONCRETE_STRING = "x=3;z=7;"
    assignment = AnyOf(alphas, is_label=True, store=True) + AnyOf("=", default="=") + AnyOf(nums, store=True) + AnyOf(";", default=";")
    lens = OneOrMore(Group(assignment, store=True))
    token = lens.get(CONCRETE_STRING, check_fully_consumed=False)
    assert token["x"][0] == "3" and token["z"][0] == "7"

    d("PUT")
    token["x"] = ["2"]
    output = lens.put(token, CONCRETE_STRING)
    d(output)
    assert output == "x=2;z=7;"

    d("CREATE")
    output = lens.create(token)
    assert output == "x=2;z=7;"
  
    d("TYPE CASTING TEST")
    values = List(AnyOf(nums, store=True, type=int), ",")
    assign = Group(AnyOf(alphas, is_label=True) + "=" + values + ";", type=list)
    lens = OneOrMore(assign, type=dict)
    token = lens.get("x=1,2,3,4,5;y=2,4,6,8;")
    d(token)
    assert token == {"x":[1,2,3,4,5], "y":[2,4,6,8]}

    output = lens.create({"o":[1,3,5], "e":[2,4,6]})
    d(output)
    # Will be one way around or the other.
    assert output == "o=1,3,5;e=2,4,6;" or output == "e=2,4,6;o=1,3,5;"


class Until(Lens) :
  """
  Match anything up until the specified lens.
  This is useful, but not the be overused (e.g. chaining can be bad: Until("X") + Until("Y")!).
  """
  def __init__(self, lens, **kargs):
    """Use negate flag to exclude characters."""
    super(Until, self).__init__(**kargs)
    self.lens = self._preprocess_lens(lens)

  def _get(self, concrete_input_reader) :
    
    parsed_chars = ""

    # Parse as many chars as we can until the lens matches something.
    while not concrete_input_reader.is_fully_consumed() :
      try :
        start_state = concrete_input_reader.get_position_state()
        self.lens.get(concrete_input_reader)
        # Roll back the state after sucessfully getting the lens.
        concrete_input_reader.set_position_state(start_state)
        break
      except LensException:
        pass
      parsed_chars += concrete_input_reader.get_next_char()

    if not parsed_chars :
      raise LensException("Expected to get at least one character!")
    
    return parsed_chars


  def _put(self, abstract_token, concrete_input_reader) :
    # If this is PUT (vs CREATE) then consume input.
    # TODO: Could do with some better checking here, to make sure output cannot be parsed by the lens.
    lens_assert(isinstance(abstract_token, str)) # Simple check
    if concrete_input_reader :
      self.get(concrete_input_reader)
    
    return abstract_token


  @staticmethod
  def TESTS() :
    d("Testing")
    concrete_reader = ConcreteInputReader("(in the middle)")
    lens = "("+Until(")", store=True) + ")"
    token = lens.get(concrete_reader)
    d(token)
    assert concrete_reader.is_fully_consumed()
    assert token[0] == "in the middle"
    
    # PUT and CREATE
    concrete_reader.reset()
    for cr in [None, concrete_reader] :
      atr = AbstractTokenReader(["monkey"])
      output = lens.put(atr, cr)
      d(output)
      assert output == "(monkey)"

class CombineChars(Lens) :
  """Combines seperate character tokens into strings in both directions."""
  # Should this use group?
  def __init__(self, lens, **kargs):
    super(CombineChars, self).__init__(**kargs)
    self.lens = lens

  def _get(self, concrete_reader) :
    """
    Gets the token from the sub lense, checking that it contains only a list of chars (no labelled tokens) or single char
    then assembles them into a single string token.
    """
    
    token = self.lens.get(concrete_reader)
  
    # If we are a non-store return nothing now
    if not self.store :
      return None

    # If the sub-lens returned a string, 
    if isinstance(token, str) :
      lens_assert(len(token) == 1, "Expected a single char string.")
      return token

    lens_assert(token and isinstance(token, AbstractCollection), "Expected a collection of tokens")
    token_collection = token
      # Check no tokens are stored with labels - we just want a straight list of tokens.
    lens_assert(token_collection.dict.keys() == [None], "Cannot combine the output of a lens that stores tokens with labels.")
    
    string_value = ""
    for sub_token in token_collection.dict[None] :
      lens_assert(isinstance(sub_token, str) and len(sub_token) == 1, "Expect only single char tokens.")
      string_value += sub_token

    lens_assert(string_value != "", "Expected at least one char token.")

    return string_value

  def _put(self, abstract_token, concrete_input_reader) :
    
    # Expand the abstract_token into an ATR(ATC), then pass to lens.
    lens_assert(isinstance(abstract_token, str) and len(abstract_token) > 0, "Expected a non-empty string")

    token_collection = GenericCollection()
    for char in abstract_token :
      token_collection.add_token(char)

    # Return the output of the lens - using a reader in order for either combinator or simple lens to pick up as list of
    # chars or as a single char.
    return self.lens.put(AbstractTokenReader(token_collection), concrete_input_reader)

  @staticmethod
  def TESTS() :
    d("GET")
    lens = CombineChars(AnyOf(alphas, store=True) + AnyOf(nums, store=True), store=True)
    concrete_reader = ConcreteInputReader("n6xxsf")
    token = lens.get(concrete_reader)
    assert(token == "n6" and concrete_reader.get_remaining() == "xxsf")

    d("PUT")
    output = lens.put("b3", "n6xxsf")
    d(output)
    assert(output == "b3")

    # CREATE
    output = lens.create("g9")
    assert(output == "g9")

    # For good measure - GET
    lens = CombineChars(OneOrMore(AnyOf(alphas, store=True)), store=True)
    concrete_reader = ConcreteInputReader("Nick1234")
    token = lens.get(concrete_reader)
    assert(token == "Nick" and concrete_reader.get_remaining() == "1234")

    # For good measure - PUT
    concrete_reader.reset()
    output = lens.put("Ed", concrete_reader)
    assert(output == "Ed" and concrete_reader.get_remaining() == "1234")

##################################################
# Useful lenses
#

class List(And) :
  """Shortcut for defining a lens-delimetered list."""
  def __init__(self, lens, delimiter_lens, **kargs):
    super(List, self).__init__(lens, ZeroOrMore(delimiter_lens + lens), **kargs)

  @staticmethod
  def TESTS() :
    lens = List(Word(alphas, store=True), ",")
    CONCRETE_STRING = "hello,world,again"
    token = lens.get(CONCRETE_STRING)
    d(token)
    assert_match(str(token), "...['hello', 'world', 'again']...")
    output = lens.put(["one", "two"], CONCRETE_STRING)
    d(output)
    assert output == "one,two"

class NewLine(Or) :
  def __init__(self, **kargs) :
    super(NewLine, self).__init__(Literal("\n", **kargs), Empty(mode=Empty.END_OF_TEXT))

  @staticmethod
  def TESTS() :
    lens = NewLine()
    assert lens.put(AbstractTokenReader([]), "\n") == "\n"
    output = lens.create(AbstractTokenReader([]))
    assert output == "\n"
    
    lens = NewLine(store=True)
    token = lens.get("\n")
    assert token == "\n"
    
    output = lens.put(AbstractTokenReader(["\n"]), "\n")
    d("'%s'" % output)
    assert output == "\n"
    
    output = lens.create(AbstractTokenReader(["\n"]))
    assert output == "\n"

class Optional(Or) :
  def __init__(self, lens, **kargs) :
    super(Optional, self).__init__(Empty(), lens, **kargs)
 
  @staticmethod
  def TESTS() :
    for store in [True] :
      # GET
      lens = Optional(Literal("hello123", store=True))
      concrete_reader = ConcreteInputReader("hello123_end")
      token = lens.get(concrete_reader)
      d("token from %s is %s" % (lens, token))

      assert((store and token == "hello123" or token == None) and concrete_reader.get_remaining() == "_end")
      
      # This should be happy not to parse the lens, since Empty() will parse it.
      concrete_reader = ConcreteInputReader("___hello123_end")
      token = lens.get(concrete_reader)
      d(token)
      assert(token == None and concrete_reader.get_remaining() == "___hello123_end")
      
      # PUT - we'd like to show that it will put a token if possible, rather than put Empty, which is always possible.
      concrete_reader = ConcreteInputReader("hello123_end")
      atr = AbstractTokenReader(["hello123"])
      output = lens.put(atr, concrete_reader)
      assert(output == "hello123" and concrete_reader.get_remaining() == "_end")
      if store:
        assert not atr.has_more_tokens_with_label(None)
      else :  
        assert atr.has_more_tokens_with_label(None)
     
      # CREATE
      output = lens.create(AbstractTokenReader(["hello123"]))
      if store:
        assert(output == "hello123")
      else :  
        assert(output == "") # Uses default value of Empty(), the first sub-lens
     
      output = lens.create(AbstractTokenReader([]))
      d(output)
      if store:
        assert(output == "") # Since it looks for but cannot find suitable token, Empty() is created with default value ''.
      else :  
        assert(output == "") # Uses default value of Empty(), the first sub-lens

class ZeroOrMore(Optional) :
  def __init__(self, lens, **kargs):
    super(ZeroOrMore, self).__init__(OneOrMore(lens), **kargs)

  @staticmethod
  def TESTS() :
    # Just test we can build the thing.
    lens = ZeroOrMore(AnyOf(alphas, store=True))
    lens.get("abcd123", check_fully_consumed=False)
    lens.get("123", check_fully_consumed=False)



class Literal(CombineChars) :
  """A lens that deals with a constant string, usually that will not be stored."""

  def __init__(self, literal_string, **kargs):
    """We create this from CombineChars(AnyOf() + ...) for consistency rather than for efficiency."""

    assert(isinstance(literal_string, str) and len(literal_string) > 0)
    super(Literal, self).__init__(None, **kargs) # Pass None for the lens, which we will build next.
    
    # Build up the lens.
    self.lens = None
    for char in literal_string :
      if not self.lens :
        self.lens = AnyOf(char, store=self.store)
      else :
        self.lens += AnyOf(char, store=self.store)
    
    self.literal_string = literal_string
    self.name = self.name or truncate(literal_string)

    if not self.default :
      self.default = literal_string

  @staticmethod
  def TESTS() :
    for store in [False, True] :
      # GET
      lens = Literal("hello", store=store)
      concrete_reader = ConcreteInputReader("helloworld")
      token = lens.get(concrete_reader)
      d(token)
      assert((store and token == "hello" or token == None) and concrete_reader.get_remaining() == "world")
      
      # PUT
      concrete_reader.reset()
      output = lens.put(AbstractTokenReader(store and ["hello"] or []), concrete_reader)
      d(output)
      assert(output == "hello" and concrete_reader.get_remaining() == "world")
      
      # CREATE
      output = lens.create(AbstractTokenReader(store and ["hello"] or []))
      d(output)
      assert(output == "hello")

    # Test literal as string concatenation - will faile without correct operator overloading.
    lens = AnyOf("X") + "my_literal"
    lens = "my_literal" + AnyOf("X")  # Uses Lens.__radd__()

class Word(CombineChars) :
  
  def __init__(self, body_chars, init_chars=None, negate=False, **kargs):
    super(Word, self).__init__(None, **kargs)
     
    if init_chars :
      self.lens = AnyOf(init_chars, negate=negate, store=self.store) + OneOrMore(AnyOf(body_chars, negate=negate, store=self.store))
    else :
      self.lens = OneOrMore(AnyOf(body_chars, negate=negate, store=self.store))

  @staticmethod
  def TESTS() :
    for store in [True, False] :
      # GET
      lens = Word(alphanums, init_chars=alphas, store=store, default="thisis123valid") # A word that can contain but not begin with a number.
      concrete_reader = ConcreteInputReader("hellomonkey123_456")
      token = lens.get(concrete_reader)
      d(token)
      if store :
        assert(token == "hellomonkey123" and concrete_reader.get_remaining() == "_456")
      else :
        assert(concrete_reader.get_remaining() == "_456")
      
      # PUT
      concrete_reader.reset()
      output = lens.put(AbstractTokenReader(["hello456"]), concrete_reader)
      assert(store and output == "hello456" or output == "hellomonkey123" and concrete_reader.get_remaining() == "_456")
      
      # CREATE
      output = lens.create(AbstractTokenReader(["hello456"]))
      assert(store and output == "hello456" or output == "thisis123valid")

    d("Type tests")
    lens = Word(nums, store=True, type=int)
    assert lens.get("3456") == 3456
    assert lens.put(98765, "123") == "98765"

class Whitespace(CombineChars) :
  """Whitespace helper lens, that knows how to handle continued lines with '\\n' or that preclude an indent."""
  
  def __init__(self, default=" ", space_chars=" \t", slash_continuation=False, indent_continuation=False, **kargs):
    kargs["default"] = default
    super(Whitespace, self).__init__(None, **kargs)
      
    spaces = OneOrMore(AnyOf(space_chars, store=self.store))
    self.lens = spaces   \
                | (Optional(spaces) + "\\\n" + Optional(spaces)) \
                | (Optional(spaces) + "\n" + spaces)  
    self.lens = spaces
    if slash_continuation :
      self.lens |= Optional(spaces) + "\\\n" + Optional(spaces)
    if indent_continuation :
      self.lens |= Optional(spaces) + "\n" + spaces 
    
    # If the default string is empty, then make the space optional.
    if default == "" :
      self.lens = Optional(self.lens)
  
  @staticmethod
  def TESTS() :
    lens = Whitespace(" ", store=True) + Word(alphanums, store=True)
    token = lens.get("  \thello")
    d(token)


####################################
# Utility functions
#


def lens_assert(condition, message=None) :
  if not condition :
    raise LensException(message)


##################################
# Useful definitions
#

# Some useful character sets.
import string
alphas    = string.lowercase + string.uppercase
nums      = string.digits
hexnums   = nums + "ABCDEFabcdef"
alphanums = alphas + nums

# Some lens abreviations
ZM  = ZeroOrMore
OM  = OneOrMore
O   = Optional
G   = Group
WS  = Whitespace


##################################
# Useful API functions, particularly since they coerce the first arg to a lens.
#

def get(lens, *args, **kargs) :
  lens = coerce_to_lens(lens)
  return lens.get(*args, **kargs)

def put(lens, *args, **kargs) :
  lens = coerce_to_lens(lens)
  return lens.put(*args, **kargs)
create = put

###########################
# Debugging stuff.
#

def debug_indent_function() :
 
  import inspect 

  # Create a list of all function names in the trace.
  function_names = []

  # Prepend the callers location to the message.
  callerFrame = inspect.currentframe()
  while callerFrame :
    location = callerFrame.f_code.co_name
    function_names.append(location)
    callerFrame = callerFrame.f_back

  #indent = max(function_names.count("put"), function_names.count("get"))
  indent = 0
  for name in ["put", "get", "_put", "_get"] :
    indent += function_names.count(name)
  indent -= 1
  indent = max(0, indent)

  #print ">>>: " +str(function_names)
 
  return " "*indent

from nbdebug import set_indent_function
set_indent_function(debug_indent_function)

#
# Testing
# 

def assert_match(input_string, template) :
  """Check if a string matches a template containing ellipses, for debugging."""
  # TODO: Might be an idea just to strip out whitespace completely and compare char string - or even to use a hash.
  import re
  import doctest

  # Replace \s*\n+\s* with '...', which means we can put our templates on multiple lines and indent them.
  subst_regex=re.compile(r"\s*\n+\s*")
  template = subst_regex.sub("...", template)

  # Hmmm, does this disgregard python comments?
  match = doctest._ellipsis_match(template, input_string)
  assert match, "Did not expect '%s'" % input_string

#
# Integrated Tests - move these to another module
#

def deb_xxxtest() :

  INPUT = """Build-Depends: debhelper (>= 7.0.0),
                 perl-modules (>= 5.10) | libmodule-build-perl,
                 perl (>= 5.8.8-12), \
               libcarp-assert-more-perl [!amd64],
                 libconfig-tiny-perl, libexception-class-perl | someapp | someotherapp (> 1.2),
                 libparse-recdescent-perl ( >= 1.90.0),
                 liblog-log4perl-perl (>= 1.11)  [i386]"""
  # In this case, a space is also a space followed by a newline followed by an indent
  

  def ws(default_output) :
    return WS(default_output, slash_continuation=True, indent_continuation=True)

  def Between(lens_1, lens_2, label=None):
    return lens_1 + Until(lens_2, store=True, label=label) + lens_2

  keyword_chars = alphanums + "-"
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
    print(output)

  # Change some things
  del token.dict[None][5]
  output = lens.put(token, INPUT)
  print(output)
  
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
  
  class Interface:
    __lens__ = "iface" + ws + label + ws + with_label("address_family") + ws + with_label("method") + nl\
    + ZM(indent + G(label + ws + Until(nl, store=True), type=auto_list)+nl)

  lens = Group(Interface.__lens__, type=Interface)
  interface = lens.get(INPUT, check_fully_consumed=False)
  d(interface.__dict__)

  assert interface.address_family == "inet"
  assert interface.address == "67.207.128.159"

  interface.address_family = "fam"
  interface.gateway = "127.0.0.1"

  output = lens.put(interface, INPUT, label="wlan2")
  d(output)
  output = lens.create(interface, label="wlan2")
  d(output)
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

def tests(args) :
  unit_tests(args)

def auto_name_lenses(local_variables) :
  for variable_name, obj in local_variables.iteritems() :
    if isinstance(obj, BaseLens) :
      obj.name = variable_name


def unit_tests(args=None) :
  
  import unittest

  # Discover test routines.
  TESTS = {}
  for name, item in globals().iteritems() :
    if name.lower().endswith("_test") :
      TESTS[name] = item
    if hasattr(item, "TESTS"):
      TESTS[item.__name__] = item.TESTS

  test_name = args[-1]
  if test_name == "test" :
    test_name = None

  if test_name and test_name not in TESTS :
    raise Exception("There is not test called: %s" % test_name)

  test_suite = unittest.TestSuite()
  for name, test_function in TESTS.iteritems() :
    if test_name and name != test_name :
      continue
    testcase = unittest.FunctionTestCase(test_function, description=name)
    test_suite.addTest(testcase)
  
  runner = unittest.TextTestRunner()
  runner.run(test_suite)



###########################
# Main.
#

def main() :
  # This can be useful for testing.
  pass

if __name__ == "__main__":
  import sys
  # Optionally run tests.
  if "test" in sys.argv :
    print("*\n"*3)
    print("Running tests")
    print("*\n"*3)
    tests(sys.argv)
  else :
    main()
