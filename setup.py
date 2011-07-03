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
from distutils.core import setup

from pylens import version

# Add distutils extensions.
sys.path.append("third_party")
import sphinx_pypi_upload


data_files = [ ]

setup(
  name='pylens',
  version=version.VERSION,
  author='Nick Blundell',
  author_email='blundeln [AT] gmail [DOT] com',
  url='http://www.nickblundell.org.uk',
  license='BSD',
  description="Pylens - Object Serialisation through a Lens",
  #long_description=open('README.rst').read(),
  requires = [
    "python (< 3.0)",
  ],
  # See http://pypi.python.org/pypi?%3Aaction=list_classifiers
  classifiers = [
    "Topic :: Text Processing",
  ],
  packages=['pylens'],
  data_files=data_files,
  cmdclass = {
    "upload_docs": sphinx_pypi_upload.UploadDoc,
  }
)
