# -*- coding: iso-8859-1 -*-
# pylint-version = 0.7.0
#
# Copyright 2005 André Malo or his licensors, as applicable
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
Trac_ repository browser URL construction

.. _`Trac`: http://www.edgewall.com/trac/
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Generator']

# global imports
import posixpath
from svnmailer.browser import _base


class Generator(_base.BaseGenerator):
    """ Trac_ template generator

        .. _`Trac`: http://www.edgewall.com/trac/
    """

    def _createTemplate(self, base_url, config):
        """ Returns Trac URL templates """
        config # pylint

        url = self._createParsedUrl(base_url)
        while url.path[-1:] == '/':
            url.path = url.path[:-1]
        dirname, basename = posixpath.split(url.path)
        url.path = dirname
        join = posixpath.join

        tpl = {
            'revision': (join(u"changeset", self._REVISION), {
                'remove': [u"rev"]
            }),

            'deleted': (join(u"file", self._BASE_PATH), {
                'set': [(u"rev", self._BASE_REVISION)]
            }),

            'deleted_dir': (join(basename, self._BASE_PATH, u""), {
                'set': [(u"rev", self._BASE_REVISION)]
            }),

            'added': (join(u"file", self._PATH), {
                'set': [(u"rev", self._REVISION)]
            }),

            'added_dir': (join(basename, self._PATH, u""), {
                'set': [(u"rev", self._REVISION)]
            }),
        }
        # no single diff support right now
        tpl['copied'] = tpl['modified'] = tpl['added']

        return _base.Template.fromTemplates(url, tpl)
