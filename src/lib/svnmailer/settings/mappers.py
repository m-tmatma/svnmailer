# -*- coding: iso-8859-1 -*-
# pylint: disable-msg=W0201
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
====================
 Plain Value Mapper
====================

The mapper provided by the `PlainMapper` class maps value according to
configured mapping sections.
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Error', 'ConfigMappingSectionNotFoundError', 'PlainMapper']

# global imports
from svnmailer.settings import _base

# exceptions
class Error(_base.Error):
    """ Base exception for this module """
    pass

class ConfigMappingSectionNotFoundError(Error):
    """ Config mapping section was not found """
    pass


class PlainMapper(_base.BaseMapper):
    """ Plain Mapper Generator

        :ivar `_to_remove`: The sections to remove (``['name', ...]``)
        :type `_to_remove`: ``list``
    """

    def init(self):
        """ Custom Initialization """
        self._to_remove = []


    def create(self, spec):
        """ Returns a plain mapper """
        if spec.startswith('[') and spec.endswith(']'):
            section = spec[1:-1]
            self._to_remove.append(section)
            return self._generateMapper(section)

        return None


    def cleanup(self):
        """ Removes all eaten map sections """
        while self._to_remove:
            section = self._to_remove.pop()
            try:
                del self._config[section]
            except KeyError:
                """ prolly already deleted... """
                pass


    def _generateMapper(self, section):
        """ Generates a mapper for a particular section

            :param `section`: The mapping section
            :type `section`: ``str``

            :return: The mapping function
            :rtype: ``callable``

            :exception ConfigMappingSectionNotFoundError: The specified
                                                          section was not found
        """
        try:
            mdict = dict([(option, value) for option, value in
                self._config.extractSection(
                    section, xform = False, keep = True, check = False
                )
            ])
        except _base.Error, exc:
            raise ConfigMappingSectionNotFoundError(str(exc))

        def mapfunc(value):
            """ Mapping function """
            return mdict.get(value, value)

        return mapfunc
