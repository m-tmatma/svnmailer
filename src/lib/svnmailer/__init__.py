# -*- coding: iso-8859-1 -*-
# pylint: disable-msg=W0103
#
# Copyright 2004-2005 André Malo or his licensors, as applicable
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This is the core svnmailer package. It contains all logic to send
subversion commit mails. The package is intended to be used by
the svn-mailer command line script.

@var version: Version of the svnmailer package
@type version: C{str}

@var is_dev: is development version?
@type is_dev: C{bool}
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__pylintver__ = "0.6.4"

version = "1.0.3"
is_dev = False

if is_dev:
    if "1.0.3".find("@VERSION@") == -1: # dev release
        version = "1.0.3"
    else:
        version = "%s-dev" % version
