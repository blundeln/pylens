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

import glob
import os

try :
  from nbdebug import d
except ImportError:
  def d(*args, **kargs):pass

def run(command) :
  d(command)
  os.system(command)

def distribute() :
  # Store the source root dir.
  # TODO: Generate sphinx docs for the package and for upload to a web server.
  SOURCE_DIR = os.getcwd()
  
  # Create docs.
  run("cp README.rst README") # For PyPi
  
  # Remove all old dist files
  run("rm -rf dist")
  
  # Create a source distribution.
  run("python2 setup.py sdist")
  
  # Extract the package for inspection.
  os.chdir("dist")
  source_package = glob.glob("pylens*.gz")[0]
  package_root = source_package.replace(".tar.gz", "")
  run("tar xzf %s" % source_package)
  os.chdir(package_root)
  
  # Run tests on packaged code, and if a single test fails, this will raise an
  # exception and abort our distribution.
  run("python2 scripts/run_tests.py all_tests")

  # TODO: Upload package and docs to PyPi.
  # TODO: Test local installation - perhaps not necessary.

if __name__ == "__main__" :
  distribute()
