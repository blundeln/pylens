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
# 
#

import os
import sys
import re

SOURCE_DIR = os.getcwd()

try :
  from nbdebug import d
except ImportError:
  def d(*args, **kargs):pass

def run(command) :
  d(command)
  return os.system(command)

def generate_pages_from_example_code(python_file) :
  d(python_file)
  
  content = open(python_file).read()

  while True:
    # Match the test function.
    match = re.search("def\s+(.+?)_test", content, re.DOTALL)
    if not match :
      break
    
    d(match.group(1))
    content = content[match.end(0):]
    
    # Now try to match comments and code.
    match = re.search("\"\"\"(.+?)\"\"\"", content, re.DOTALL)
    if match :
      d(match.group(1))
      content = content[match.end(0):]

    match = re.search("#(.+?)\n", content, re.DOTALL)
    if match :
      d(match.group(1))
      content = content[match.end(0):]
    
  
  return
  lines = open(python_file).readlines()
  pages = {}
  current_page = None
  current_text = []
  current_code = []
  for line in lines:
    
    # Start a new page from the test function.
    match = re.search("def\s+(.+)_test", line)
    if match: 
      current_page = match.group(1)
      pages[current_page] = []
      

  d(pages)

def generate_docs_from_example_tests():
  d("sds")
 
  generate_pages_from_example_code(os.path.join(SOURCE_DIR, "examples/basic.py"))
  sys.exit(0)

def main():
  
  # Generate tutorials from source.
  generate_docs_from_example_tests()
  

  # Generate index.rst from our README file.
  index_content = open("README.rst").read()
  index_content = index_content.replace(".. TOC", "\n\n\n" + open("docs/source/master_toc").read())
  open("docs/source/index.rst", "w").write(index_content)
 

  exit_code = run("sphinx-build -W -b html docs/source docs/build/html")
  if exit_code :
    raise Exception("Sphinx build failed")

if __name__ == "__main__" :
  main()
