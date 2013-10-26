# -*- coding: utf-8 -*-
# pylint: disable-msg=W0621,W0103
# pylint-version = 0.7.0
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
This is the svnmailer package. It contains all logic to post subversion
event notifications. The package is intended to be used by the ``svn-mailer``
command line script.

:Variables:
 - `version`: Version of the svnmailer package

:Types:
 - `version`: `_Version`
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"


class _Version(object):
    """ Represents the svnmailer version

        :IVariables:
         - `major`: The major version number
         - `minor`: The minor version number
         - `patch`: The patch level number
         - `is_dev`: Is it a development version?
         - `string`: Full version string

        :Types:
         - `major`: ``int``
         - `minor`: ``int``
         - `patch`: ``int``
         - `is_dev`: ``bool``
         - `string`: ``str``
    """
    def __init__(self, injected, version, is_dev):
        """ Initialization

            :Parameters:
             - `injected`: A version string injected by the release build
               system for dev releases. If it contains the string
               ``@VERSION@`` and `is_dev` is ``True``, it's assumed, that
               no string was injected and the final version string is just
               `version` + ``"-dev"``

             - `version`: The numbered version string (like ``"1.1.0"``)
               It has to contain exactly three numbers; dot separated

             - `is_dev`: Is it a development version?

            :Types:
             - `injected`: ``str``
             - `version`: ``str``
             - `is_dev`: ``bool``
        """
        self.major, self.minor, self.patch = [
            int(item) for item in version.split('.')
        ]

        if is_dev:
            if injected.find("@VERSION@") == -1: # dev release
                version = injected
            else:                                # svn checkout
                version = "%s-dev" % version

        self.is_dev = is_dev
        self.string = version


    def __repr__(self):
        """ Returns a string representation """
        return "<svnmailer.version %s>" % self.string


version = _Version(
    injected = "1.1.0-dev-r1373",
    version  = "1.1.0",
    is_dev   = True,
)
