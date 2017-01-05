# Copyright (c) 2010, Columbia Center For New Media Teaching And Learning (CCNMTL)
# Copyright (c) 2012-2017, havard@gulldahl.no
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the CCNMTL nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY CCNMTL ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <copyright holder> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from setuptools import setup, find_packages

setup(
    name="xmeml-iter",
    author="Havard Gulldahl",
    author_email="havard@gulldahl.no",
    url="http://github.com/havardgulldahl/xmeml/",
    description="Iterative parser for Final Cut Pro <xmeml> files - based on lxml",
    long_description="Parse and analyze FCP xml files. Supports files from Final Cut Pro 7x and Adobe Premiere. This is a fork of the original xmeml project that adds support for the iter protocol for fast parsing, as well as some audio analysis functions. ",
    scripts = [],
    license = "BSD",
    platforms = ["any"],
    zip_safe=False,
    packages=find_packages(),
    )
    
